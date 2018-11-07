#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

GIT_PROJECT_DIR=$(mktemp -d)

function setup_openstack_clients {
    # Prepare virtualenv for openstack deployment tests
    virtualenv ~/openstackclient-venv
    ~/openstackclient-venv/bin/pip install -U pip
    ~/openstackclient-venv/bin/pip install python-openstackclient
    if [[ $ACTION == zun ]]; then
        ~/openstackclient-venv/bin/pip install python-zunclient
    fi
    if [[ $ACTION == ironic ]]; then
        ~/openstackclient-venv/bin/pip install python-ironicclient
    fi
    if [[ $ACTION == masakari ]]; then
        ~/openstackclient-venv/bin/pip install python-masakariclient
    fi
}

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
        GATE_IMAGES="cron,fluentd,glance,haproxy,keepalived,keystone,kolla-toolbox,mariadb,memcached,neutron,nova,openvswitch,rabbitmq,horizon,chrony,heat,placement"
    else
        GATE_IMAGES="bifrost"
    fi

    if [[ $ACTION =~ "ceph" ]]; then
        GATE_IMAGES+=",ceph,cinder"
    fi

    if [[ $ACTION == "cinder-lvm" ]]; then
        GATE_IMAGES+=",cinder,iscsid,tgtd"
    fi

    if [[ $ACTION == "zun" ]]; then
        GATE_IMAGES+=",zun,kuryr,etcd"
    fi

    if [[ $ACTION == "scenario_nfv" ]]; then
        GATE_IMAGES+=",tacker,mistral,redis,barbican"
    fi
    if [[ $ACTION == "ironic" ]]; then
        GATE_IMAGES+=",dnsmasq,ironic,iscsid"
    fi
    if [[ $ACTION == "masakari" ]]; then
        GATE_IMAGES+=",masakari"
    fi

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
template_override = /etc/kolla/template_overrides.j2

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

    # Test latest ansible version on Ubuntu, minimum supported on others.
    if [[ $BASE_DISTRO == "ubuntu" ]]; then
        ANSIBLE_VERSION=">=2.5"
    else
        ANSIBLE_VERSION="<2.6"
    fi

    # TODO(SamYaple): Move to virtualenv
    sudo pip install -U "ansible${ANSIBLE_VERSION}" "ara<1.0.0"

    detect_distro

    sudo mkdir /etc/ansible
    ara_location=$(python -m ara.setup.callback_plugins)
    sudo tee /etc/ansible/ansible.cfg<<EOF
[defaults]
callback_plugins = ${ara_location}
host_key_checking = False
EOF

    # Record the running state of the environment as seen by the setup module
    ansible all -i ${RAW_INVENTORY} -e ansible_user=$USER -m setup > /tmp/logs/ansible/initial-setup
}

function setup_node {
    ansible-playbook -i ${RAW_INVENTORY} -e ansible_user=$USER tools/playbook-setup-nodes.yml
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

setup_openstack_clients

setup_ansible
setup_config
setup_node

tools/kolla-ansible -i ${RAW_INVENTORY} -e ansible_user=$USER -vvv bootstrap-servers &> /tmp/logs/ansible/bootstrap-servers
prepare_images
