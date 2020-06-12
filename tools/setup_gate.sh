#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function setup_openstack_clients {
    # Prepare virtualenv for openstack deployment tests
    local packages=(python-openstackclient python-heatclient)
    if [[ $SCENARIO == zun ]]; then
        packages+=(python-zunclient)
    fi
    if [[ $SCENARIO == ironic ]]; then
        packages+=(python-ironicclient)
    fi
    if [[ $SCENARIO == masakari ]]; then
        packages+=(python-masakariclient)
    fi
    if [[ $SCENARIO == scenario_nfv ]]; then
        packages+=(python-tackerclient python-barbicanclient python-mistralclient)
    fi
    if [[ "debian" == $BASE_DISTRO ]]; then
        sudo apt -y install python3-venv
    fi
    python3 -m venv ~/openstackclient-venv
    ~/openstackclient-venv/bin/pip install -U pip
    ~/openstackclient-venv/bin/pip install -c $UPPER_CONSTRAINTS ${packages[@]}
}

function prepare_images {
    if [[ "${BUILD_IMAGE}" == "False" ]]; then
        return
    fi

    if [[ $SCENARIO != "bifrost" ]]; then
        GATE_IMAGES="^cron,^fluentd,^glance,^haproxy,^keepalived,^keystone,^kolla-toolbox,^mariadb,^memcached,^neutron,^nova-,^openvswitch,^rabbitmq,^horizon,^chrony,^heat,^placement"
    else
        GATE_IMAGES="bifrost"
    fi

    if [[ $SCENARIO == "ceph-ansible" ]]; then
        GATE_IMAGES+=",^cinder"
    fi

    if [[ $SCENARIO == "zun" ]]; then
        GATE_IMAGES+=",^zun,^kuryr,^etcd,^cinder,^iscsid"
        if [[ $BASE_DISTRO != "centos" ]]; then
            GATE_IMAGES+=",^tgtd"
        fi
    fi

    if [[ $SCENARIO == "scenario_nfv" ]]; then
        GATE_IMAGES+=",^tacker,^mistral,^redis,^barbican"
    fi
    if [[ $SCENARIO == "ironic" ]]; then
        GATE_IMAGES+=",^dnsmasq,^ironic,^iscsid"
    fi
    if [[ $SCENARIO == "masakari" ]]; then
        GATE_IMAGES+=",^masakari"
    fi

    if [[ $SCENARIO == "swift" ]]; then
        GATE_IMAGES+=",^swift"
    fi

    if [[ $SCENARIO == "ovn" ]]; then
        GATE_IMAGES+=",^ovn"
    fi

    if [[ $SCENARIO == "mariadb" ]]; then
        GATE_IMAGES="^cron,^fluentd,^haproxy,^keepalived,^kolla-toolbox,^mariadb"
    fi

    # NOTE(yoctozepto): we cannot build and push at the same time on debian
    # buster see https://github.com/docker/for-linux/issues/711.
    PUSH="true"
    if [[ "debian" == $BASE_DISTRO ]]; then
        PUSH="false"
    fi

    sudo tee /etc/kolla/kolla-build.conf <<EOF
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
# NOTE(yoctozepto): to avoid issues with IPv6 not enabled in the docker daemon
# and since we don't need isolated networks here, use host networking
network_mode = host

[profiles]
gate = ${GATE_IMAGES}
EOF

    mkdir -p /tmp/logs/build

    sudo docker run -d -p 4000:5000 --restart=always -v /opt/kolla_registry/:/var/lib/registry --name registry registry:2

    python3 -m venv ~/kolla-venv
    . ~/kolla-venv/bin/activate

    pip install "${KOLLA_SRC_DIR}"

    sudo ~/kolla-venv/bin/kolla-build

    # NOTE(yoctozepto): due to debian buster we push after images are built
    # see https://github.com/docker/for-linux/issues/711
    if [[ "debian" == $BASE_DISTRO ]]; then
        for img in $(sudo docker image ls --format '{{ .Repository }}:{{ .Tag }}' | grep lokolla/); do
            sudo docker push $img;
        done
    fi

    deactivate
}


setup_openstack_clients

RAW_INVENTORY=/etc/kolla/inventory
tools/kolla-ansible -i ${RAW_INVENTORY} -e ansible_user=$USER -vvv bootstrap-servers &> /tmp/logs/ansible/bootstrap-servers

prepare_images
