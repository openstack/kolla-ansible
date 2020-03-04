#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

GIT_PROJECT_DIR=$(mktemp -d)

function setup_config {
    # Use Infra provided pypi.
    # Wheel package mirror may be not compatible. So do not enable it.
    PIP_CONF=$(mktemp)
    cat > ${PIP_CONF} <<EOF
[global]
timeout = 60
index-url = $NODEPOOL_PYPI_MIRROR
trusted-host = $NODEPOOL_MIRROR_HOST
EOF
    echo "RUN echo $(base64 -w0 ${PIP_CONF}) | base64 -d > /etc/pip.conf" | sudo tee /etc/kolla/header
    rm ${PIP_CONF}

    if [[ $ACTION != "bifrost" ]]; then
        GATE_IMAGES="cron,fluentd,glance,haproxy,keepalived,keystone,kolla-toolbox,mariadb,memcached,neutron,nova,openvswitch,rabbitmq,horizon,chrony"
    else
        GATE_IMAGES="bifrost"
    fi

    if [[ $ACTION =~ "ceph" ]]; then
        GATE_IMAGES+=",ceph,cinder"
    fi

    if [[ $ACTION == "zun" ]]; then
        GATE_IMAGES+=",zun,kuryr"
    fi

    # Use the kolla-ansible tag rather than the kolla tag, since this is what
    # kolla-ansible will use by default.
    TAG=$(python -c "import pbr.version; print(pbr.version.VersionInfo('kolla-ansible'))")
    cat <<EOF | sudo tee /etc/kolla/kolla-build.conf
[DEFAULT]
include_header = /etc/kolla/header
namespace = lokolla
base = ${BASE_DISTRO}
install_type = ${INSTALL_TYPE}
tag = ${TAG}
profile = gate
registry = 127.0.0.1:4000
push = true
logs_dir = /tmp/logs/build

[profiles]
gate = ${GATE_IMAGES}
EOF

mkdir -p /tmp/logs/build

    if [[ "${DISTRO}" == "Debian" ]]; then
        # Infra does not sign their mirrors so we ignore gpg signing in the gate
        echo "RUN echo 'APT::Get::AllowUnauthenticated \"true\";' > /etc/apt/apt.conf" | sudo tee -a /etc/kolla/header

        # Optimize the repos to take advantage of the Infra provided mirrors for Ubuntu
        cat << EOF | sudo tee -a /etc/kolla/kolla-build.conf
apt_sources_list = /etc/kolla/sources.list
EOF
        sudo cp /etc/apt/sources.list /etc/kolla/sources.list
        sudo cat /etc/apt/sources.list.available.d/ubuntu-cloud-archive-pike.list | sudo tee -a /etc/kolla/sources.list
        # Append non-infra provided repos to list
        cat << EOF | sudo tee -a /etc/kolla/sources.list
deb http://nyc2.mirrors.digitalocean.com/mariadb/repo/10.0/ubuntu xenial main
deb http://repo.percona.com/apt xenial main
deb http://packages.elastic.co/elasticsearch/2.x/debian stable main
deb http://packages.elastic.co/kibana/4.6/debian stable main
EOF
    fi
}

function detect_distro {
    DISTRO=$(ansible all -i "localhost," -msetup -clocal | awk -F\" '/ansible_os_family/ {print $4}')
}

function setup_ansible {
    RAW_INVENTORY=/etc/kolla/inventory

    # Test Ansible 2.8.x on Ubuntu, minimum supported on others.
    if [[ $BASE_DISTRO == "ubuntu" ]]; then
        ANSIBLE_VERSION=">=2.4,<2.9"
        ARA_VERSION="<1.0.0"
    else
        ANSIBLE_VERSION="<2.5"
        ARA_VERSION="<0.16"
    fi
    # TODO(SamYaple): Move to virtualenv
    sudo -H pip install -U "ansible${ANSIBLE_VERSION}" "docker>=2.0.0" "python-openstackclient" "ara${ARA_VERSION}" "cmd2<0.9.0" "pyfakefs<4"
    if [[ $ACTION == "zun" ]]; then
        sudo -H pip install -U "python-zunclient"
    fi
    detect_distro

    sudo mkdir /etc/ansible
    ara_location=$(python -m ara.setup.callback_plugins)
    sudo tee /etc/ansible/ansible.cfg<<EOF
[defaults]
callback_plugins = ${ara_location}
host_key_checking = False
EOF

    # Record the running state of the environment as seen by the setup module
    ansible all -i ${RAW_INVENTORY} -m setup > /tmp/logs/ansible/initial-setup
}

function setup_node {
    ansible-playbook -i ${RAW_INVENTORY} tools/playbook-setup-nodes.yml
}

function prepare_images {
    if [[ "${BUILD_IMAGE}" == "False" ]]; then
        return
    fi
    sudo docker run -d -p 4000:5000 --restart=always -v /opt/kolla_registry/:/var/lib/registry --name registry registry:2
    pushd "${KOLLA_SRC_DIR}"
    sudo tox -e "build-${BASE_DISTRO}-${INSTALL_TYPE}"
    popd
}

function sanity_check {
    # Wait for service ready
    sleep 15
    . /etc/kolla/admin-openrc.sh
    # TODO(Jeffrey4l): Restart the memcached container to cleanup all cache.
    # Remove this after this bug is fixed
    # https://bugs.launchpad.net/oslo.cache/+bug/1590779
    sudo docker restart memcached
    nova --debug service-list
    openstack --debug network agent list
    tools/init-runonce
    nova --debug boot --poll --image $(openstack image list | awk '/cirros/ {print $2}') --nic net-id=$(openstack network list | awk '/demo-net/ {print $2}') --flavor 1 kolla_boot_test

    nova --debug list
    # If the status is not ACTIVE, print info and exit 1
    nova --debug show kolla_boot_test | awk '{buf=buf"\n"$0} $2=="status" && $4!="ACTIVE" {failed="yes"}; END {if (failed=="yes") {print buf; exit 1}}'
    if echo $ACTION | grep -q "ceph"; then
        openstack volume create --size 2 test_volume
        attempt=1
        while [[ $(openstack volume show test_volume -f value -c status) != "available" ]]; do
            echo "Volume not available yet"
            attempt=$((attempt+1))
            if [[ $attempt -eq 10 ]]; then
                echo "Volume failed to become available"
                openstack volume show test_volume
                return 1
            fi
            sleep 10
        done
        openstack server add volume kolla_boot_test test_volume --device /dev/vdb
        attempt=1
        while [[ $(openstack volume show test_volume -f value -c status) != "in-use" ]]; do
            echo "Volume not attached yet"
            attempt=$((attempt+1))
            if [[ $attempt -eq 10 ]]; then
                echo "Volume failed to attach"
                openstack volume show test_volume
                return 1
            fi
            sleep 10
        done
        openstack server remove volume kolla_boot_test test_volume
        attempt=1
        while [[ $(openstack volume show test_volume -f value -c status) != "available" ]]; do
            echo "Volume not detached yet"
            attempt=$((attempt+1))
            if [[ $attempt -eq 10 ]]; then
                echo "Volume failed to detach"
                openstack volume show test_volume
                return 1
            fi
            sleep 10
        done
        openstack volume delete test_volume
    fi
    if echo $ACTION | grep -q "zun"; then
        openstack --debug appcontainer service list
        openstack --debug appcontainer host list
        # TODO(hongbin): Run a Zun container and assert the container becomes
        # Running
    fi
}

function test_openstack {
    # Create dummy interface for neutron
    ansible -m shell -i ${RAW_INVENTORY} -a "ip l a fake_interface type dummy" all

    #TODO(inc0): Post-deploy complains that /etc/kolla is not writable. Probably we need to include become there
    sudo chmod -R 777 /etc/kolla
    # Actually do the deployment
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks > /tmp/logs/ansible/prechecks1
    # TODO(jeffrey4l): add pull action when we have a local registry
    # service in CI
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv deploy > /tmp/logs/ansible/deploy
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv post-deploy > /tmp/logs/ansible/post-deploy
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv check > /tmp/logs/ansible/check-deploy

    # Test OpenStack Environment
    # TODO: use kolla-ansible check when it's ready

    sanity_check

    # TODO(jeffrey4l): make some configure file change and
    # trigger a real reconfigure
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv reconfigure >  /tmp/logs/ansible/reconfigure
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv check > /tmp/logs/ansible/check-reconfigure
    # TODO(jeffrey4l): need run a real upgrade
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv upgrade > /tmp/logs/ansible/upgrade
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv check > /tmp/logs/ansible/check-upgrade

    # run prechecks again
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks > /tmp/logs/ansible/prechecks2
}

function sanity_check_bifrost {
    # TODO(mgoddard): More testing, deploy bare metal nodes.
    # TODO(mgoddard): Use openstackclient when clouds.yaml works. See
    # https://bugs.launchpad.net/bifrost/+bug/1754070.
    attempts=0
    while [[ $(sudo docker exec bifrost_deploy bash -c "OS_CLOUD=bifrost openstack baremetal driver list -f value" | wc -l) -eq 0 ]]; do
        attempts=$((attempts + 1))
        if [[ $attempts -gt 6 ]]; then
            echo "Timed out waiting for ironic conductor to become active"
            exit 1
        fi
        sleep 10
    done
    sudo docker exec bifrost_deploy bash -c "OS_CLOUD=bifrost openstack baremetal node list"
    sudo docker exec bifrost_deploy bash -c "OS_CLOUD=bifrost openstack baremetal node create --driver ipmi --name test-node"
    sudo docker exec bifrost_deploy bash -c "OS_CLOUD=bifrost openstack baremetal node delete test-node"
}

function test_bifrost {
    # TODO(mgoddard): run prechecks.

    # Deploy the bifrost container.
    # TODO(mgoddard): add pull action when we have a local registry service in
    # CI.
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv deploy-bifrost > /tmp/logs/ansible/deploy-bifrost

    # Test Bifrost Environment
    sanity_check_bifrost

    # TODO(mgoddard): make some configuration file changes and trigger a real
    # reconfigure.
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv deploy-bifrost >  /tmp/logs/ansible/deploy-bifrost2

    # TODO(mgoddard): perform an upgrade.
}

check_failure() {
    # All docker container's status are created, restarting, running, removing,
    # paused, exited and dead. Containers without running status are treated as
    # failure. removing is added in docker 1.13, just ignore it now.
    failed_containers=$(sudo docker ps -a --format "{{.Names}}" \
        --filter status=created \
        --filter status=restarting \
        --filter status=paused \
        --filter status=exited \
        --filter status=dead)

    if [[ -n "$failed_containers" ]]; then
        exit 1;
    fi
}


setup_ansible
setup_config
setup_node

tools/kolla-ansible -i ${RAW_INVENTORY} bootstrap-servers > /tmp/logs/ansible/bootstrap-servers
prepare_images

if [[ $ACTION != bifrost ]]; then
    test_openstack
else
    test_bifrost
fi

check_failure
