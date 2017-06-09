#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

source /etc/nodepool/provider

NODEPOOL_MIRROR_HOST=${NODEPOOL_MIRROR_HOST:-mirror.$NODEPOOL_REGION.$NODEPOOL_CLOUD.openstack.org}
NODEPOOL_MIRROR_HOST=$(echo $NODEPOOL_MIRROR_HOST|tr '[:upper:]' '[:lower:]')
NODEPOOL_PYPI_MIRROR=${NODEPOOL_PYPI_MIRROR:-http://$NODEPOOL_MIRROR_HOST/pypi/simple}

GIT_PROJECT_DIR=$(mktemp -d)

# Just for mandre :)
if [[ ! -f /etc/sudoers.d/jenkins ]]; then
    echo "jenkins ALL=(:docker) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/jenkins
fi

function clone_repos {
    cat > /tmp/clonemap <<EOF
clonemap:
 - name: openstack/kolla
   dest: ${GIT_PROJECT_DIR}/kolla
 - name: openstack/requirements
   dest: ${GIT_PROJECT_DIR}/requirements
EOF
    /usr/zuul-env/bin/zuul-cloner -m /tmp/clonemap --workspace "$(pwd)" \
        --cache-dir /opt/git git://git.openstack.org \
        openstack/kolla openstack/requirements
}

function setup_config {
    sudo mkdir /etc/kolla
    sudo chmod -R 777 /etc/kolla
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

    # Get base distro and install type from workspace. The full path looks like
    #   /home/jenkins/workspace/gate-kolla-ansible-dsvm-deploy-centos-source-centos-7-nv

    # NOTE(Jeffrey4l): use different a docker namespace name in case it pull image from hub.docker.io when deplying
    cat <<EOF | sudo tee /etc/kolla/kolla-build.conf
[DEFAULT]
include_header = /etc/kolla/header
namespace = lokolla
base = ${BASE_DISTRO}
install_type = ${INSTALL_TYPE}
profile = gate
registry = 127.0.0.1:4000
push = true

[profiles]
gate = cron,fluentd,glance,haproxy,keepalived,keystone,kolla-toolbox,mariadb,memcached,neutron,nova,openvswitch,rabbitmq,horizon
EOF

    if [[ "${DISTRO}" == "Debian" ]]; then
        # Infra does not sign thier mirrors so we ignore gpg signing in the gate
        echo "RUN echo 'APT::Get::AllowUnauthenticated \"true\";' > /etc/apt/apt.conf" | sudo tee -a /etc/kolla/header

        # Optimize the repos to take advantage of the Infra provided mirrors for Ubuntu
        cat << EOF | sudo tee -a /etc/kolla/kolla-build.conf
apt_sources_list = /etc/kolla/sources.list
EOF
        sudo cp /etc/apt/sources.list /etc/kolla/sources.list
        sudo cat /etc/apt/sources.list.available.d/ubuntu-cloud-archive.list | sudo tee -a /etc/kolla/sources.list
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

# NOTE(sdake): This works around broken nodepool on systems with only one
#              private interface
#              The big regex checks for IP addresses in the file
function setup_workaround_broken_nodepool {
    if [[ `grep -E -o "(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)" /etc/nodepool/node_private | wc -l` -eq 0 ]]; then
        cp /etc/nodepool/node /etc/nodepool/node_private
        cp /etc/nodepool/sub_nodes /etc/nodepool/sub_nodes_private
    fi
}

function setup_ssh {
    sudo chown jenkins /etc/nodepool/id_rsa
    sudo chmod 600 /etc/nodepool/id_rsa
}

function setup_inventory {

    echo -e "127.0.0.1\tlocalhost" > /tmp/hosts
    ansible-playbook tests/ansible_generate_inventory.yml
    sudo chown root: /tmp/hosts
    sudo chmod 644 /tmp/hosts
    sudo mv /tmp/hosts /etc/hosts
}

function setup_ansible {
    RAW_INVENTORY=/tmp/kolla/raw_inventory
    mkdir /tmp/kolla

    # TODO(SamYaple): Move to virtualenv
    sudo -H pip install -U "ansible>=2" "docker-py>=1.6.0" "python-openstackclient" "python-neutronclient" "ara"
    detect_distro

    setup_inventory

    sudo mkdir /etc/ansible
    sudo tee /etc/ansible/ansible.cfg<<EOF
[defaults]
callback_plugins = /usr/lib/python2.7/site-packages/ara/plugins/callbacks:\$VIRTUAL_ENV/lib/python2.7/site-packages/ara/plugins/callbacks
host_key_checking = False
EOF

    # Record the running state of the environment as seen by the setup module
    ansible all -i ${RAW_INVENTORY} -m setup > /tmp/logs/ansible/initial-setup
}

function setup_node {
    ansible-playbook -i ${RAW_INVENTORY} tools/playbook-setup-nodes.yml
}

function setup_logging {
    # This directory is the directory that is copied with the devstack-logs
    # publisher. It must exist at /home/jenkins/workspace/<job-name>/logs
    mkdir logs

    # For ease of access we symlink that logs directory to a known path
    ln -s $(pwd)/logs /tmp/logs
    mkdir -p /tmp/logs/{ansible,build,kolla,kolla_configs,system_logs}
}

function prepare_images {
    sudo docker run -d -p 4000:5000 --restart=always -v /tmp/kolla_registry/:/var/lib/registry --name registry registry:2

    # NOTE(Jeffrey4l): Zuul adds all changes depend on to ZUUL_CHANGES
    # variable. if find "openstack/kolla:" string, it means this patch depends
    # on one of Kolla patch. Then build image by using Kolla's code.
    # Otherwise, pull images from tarballs.openstack.org site.
    if echo "$ZUUL_CHANGES" | grep -q -i "openstack/kolla:"; then
        pushd "${GIT_PROJECT_DIR}/kolla"
        sudo tox -e "build-${BASE_DISTRO}-${INSTALL_TYPE}"
        popd
    else
        BRANCH=$(echo "$ZUUL_BRANCH" | cut -d/ -f2)
        filename=${BASE_DISTRO}-${INSTALL_TYPE}-registry-${BRANCH}.tar.gz
        wget -q -c -O "/tmp/$filename" \
            "http://tarballs.openstack.org/kolla/images/$filename"
        sudo tar xzf "/tmp/$filename" -C /tmp/kolla_registry
    fi
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
    neutron --debug agent-list
    tools/init-runonce
    nova --debug boot --poll --image $(openstack image list | awk '/cirros/ {print $2}') --nic net-id=$(openstack network list | awk '/demo-net/ {print $2}') --flavor 1 kolla_boot_test
    nova --debug list
    # If the status is not ACTIVE, print info and exit 1
    nova --debug show kolla_boot_test | awk '{buf=buf"\n"$0} $2=="status" && $4!="ACTIVE" {failed="yes"}; END {if (failed=="yes") {print buf; exit 1}}'
}

function get_logs {
    ansible-playbook -i ${RAW_INVENTORY} tests/ansible_get_logs.yml > /tmp/logs/ansible/get-logs
}

setup_logging
tools/dump_info.sh
clone_repos
setup_workaround_broken_nodepool
setup_ssh
setup_ansible
setup_config
setup_node

ansible-playbook -e type=$INSTALL_TYPE -e base=$BASE_DISTRO tests/ansible_generate_config.yml > /tmp/logs/ansible/generate_config
tools/kolla-ansible -i ${RAW_INVENTORY} bootstrap-servers > /tmp/logs/ansible/bootstrap-servers
sudo tools/generate_passwords.py
prepare_images

trap get_logs EXIT

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

# Test OpenStack Environment
# TODO: use kolla-ansible check when it's ready
sanity_check

# TODO(jeffrey4l): make some configure file change and
# trigger a real reconfigure
tools/kolla-ansible -i ${RAW_INVENTORY} -vvv reconfigure >  /tmp/logs/ansible/post-deploy
# TODO(jeffrey4l): need run a real upgrade
tools/kolla-ansible -i ${RAW_INVENTORY} -vvv upgrade > /tmp/logs/ansible/upgrade

# run prechecks again
tools/kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks > /tmp/logs/ansible/prechecks2

get_logs

ara generate html /tmp/logs/playbook_reports/
gzip --recursive --best /tmp/logs/playbook_reports/
