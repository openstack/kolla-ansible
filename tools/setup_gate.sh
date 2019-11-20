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
    ~/openstackclient-venv/bin/pip install python-heatclient
    if [[ $SCENARIO == zun ]]; then
        ~/openstackclient-venv/bin/pip install python-zunclient
    fi
    if [[ $SCENARIO == ironic ]]; then
        ~/openstackclient-venv/bin/pip install python-ironicclient
    fi
    if [[ $SCENARIO == masakari ]]; then
        ~/openstackclient-venv/bin/pip install python-masakariclient
    fi
}

function setup_config {
    if [[ $SCENARIO != "bifrost" ]]; then
        GATE_IMAGES="cron,fluentd,glance,haproxy,keepalived,keystone,kolla-toolbox,mariadb,memcached,neutron,nova,openvswitch,rabbitmq,horizon,chrony,heat,placement"
    else
        GATE_IMAGES="bifrost"
    fi

    if [[ $SCENARIO == "ceph" ]]; then
        GATE_IMAGES+=",ceph,cinder"
    fi

    if [[ $SCENARIO == "cinder-lvm" ]]; then
        GATE_IMAGES+=",cinder,iscsid,tgtd"
    fi

    if [[ $SCENARIO == "zun" ]]; then
        GATE_IMAGES+=",zun,kuryr,etcd"
    fi

    if [[ $SCENARIO == "scenario_nfv" ]]; then
        GATE_IMAGES+=",tacker,mistral,redis,barbican"
    fi
    if [[ $SCENARIO == "ironic" ]]; then
        GATE_IMAGES+=",dnsmasq,ironic,iscsid"
    fi
    if [[ $SCENARIO == "masakari" ]]; then
        GATE_IMAGES+=",masakari"
    fi

    if [[ $SCENARIO == "mariadb" ]]; then
        GATE_IMAGES="cron,haproxy,keepalived,kolla-toolbox,mariadb"
    fi

    # NOTE(yoctozepto): we cannot build and push at the same time on debian
    # buster see https://github.com/docker/for-linux/issues/711.
    PUSH="true"
    if [[ "debian" == $BASE_DISTRO ]]; then
        PUSH="false"
    fi
    cat <<EOF | sudo tee /etc/kolla/kolla-build.conf
[DEFAULT]
namespace = lokolla
base = ${BASE_DISTRO}
install_type = ${INSTALL_TYPE}
tag = ${TAG}
profile = gate
registry = 127.0.0.1:4000
push = ${PUSH}
logs_dir = /tmp/logs/build
template_override = /etc/kolla/template_overrides.j2

[profiles]
gate = ${GATE_IMAGES}
EOF

    mkdir -p /tmp/logs/build
}

function setup_ansible {
    RAW_INVENTORY=/etc/kolla/inventory

    # Test latest ansible version on Ubuntu, minimum supported on others.
    if [[ $BASE_DISTRO == "ubuntu" ]]; then
        ANSIBLE_VERSION=">=2.6"
    else
        ANSIBLE_VERSION="<2.7"
    fi

    # TODO(SamYaple): Move to virtualenv
    sudo pip install -U "ansible${ANSIBLE_VERSION}" "ara<1.0.0"

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

function prepare_images {
    if [[ "${BUILD_IMAGE}" == "False" ]]; then
        return
    fi
    sudo docker run -d -p 4000:5000 --restart=always -v /opt/kolla_registry/:/var/lib/registry --name registry registry:2
    pushd "${KOLLA_SRC_DIR}"
    sudo tox -e "build-${BASE_DISTRO}-${INSTALL_TYPE}"
    # NOTE(yoctozepto): due to debian buster we push after images are built
    # see https://github.com/docker/for-linux/issues/711
    if [[ "debian" == $BASE_DISTRO ]]; then
        for img in $(sudo docker image ls --format '{{ .Repository }}:{{ .Tag }}' | grep lokolla/); do
            sudo docker push $img;
        done
    fi
    popd
}

setup_openstack_clients

setup_ansible
setup_config

tools/kolla-ansible -i ${RAW_INVENTORY} -e ansible_user=$USER -vvv bootstrap-servers &> /tmp/logs/ansible/bootstrap-servers
prepare_images
