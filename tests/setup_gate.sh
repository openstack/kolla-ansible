#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function prepare_images {
    if [[ "${BUILD_IMAGE}" == "False" ]]; then
        return
    fi

    sudo mkdir -p /tmp/logs/build
    sudo mkdir -p /opt/kolla_registry

    sudo $CONTAINER_ENGINE run -d --net=host -e REGISTRY_HTTP_ADDR=0.0.0.0:4000 --restart=always -v /opt/kolla_registry/:/var/lib/registry --name registry quay.io/opendevmirror/registry:2


    python3 -m venv ~/kolla-venv
    source ~/kolla-venv/bin/activate
    if [[ "$CONTAINER_ENGINE" == "docker" ]]; then
        pip install "${KOLLA_SRC_DIR}" "docker"
    else
        pip install "${KOLLA_SRC_DIR}" "podman"
    fi

    sudo ~/kolla-venv/bin/kolla-build

    deactivate
}


RAW_INVENTORY=/etc/kolla/inventory

source $KOLLA_ANSIBLE_VENV_PATH/bin/activate
kolla-ansible bootstrap-servers -i ${RAW_INVENTORY} -vvv  &> /tmp/logs/ansible/bootstrap-servers
deactivate

prepare_images
