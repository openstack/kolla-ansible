#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function upgrade {
    RAW_INVENTORY=/etc/kolla/inventory

    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate

    kolla-ansible -i ${RAW_INVENTORY} -vvv certificates &> /tmp/logs/ansible/certificates
    kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks &> /tmp/logs/ansible/upgrade-prechecks
    kolla-ansible -i ${RAW_INVENTORY} -vvv pull &> /tmp/logs/ansible/pull-upgrade
    kolla-ansible -i ${RAW_INVENTORY} -vvv upgrade &> /tmp/logs/ansible/upgrade

    kolla-ansible -i ${RAW_INVENTORY} -vvv post-deploy &> /tmp/logs/ansible/upgrade-post-deploy

    kolla-ansible -i ${RAW_INVENTORY} -vvv validate-config &> /tmp/logs/ansible/validate-config
}


upgrade
