#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function upgrade {
    RAW_INVENTORY=/etc/kolla/inventory

    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate

    kolla-ansible certificates -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/certificates
    kolla-ansible prechecks -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/upgrade-prechecks
    kolla-ansible pull -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/pull-upgrade
    kolla-ansible upgrade -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/upgrade

    kolla-ansible post-deploy -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/upgrade-post-deploy

    kolla-ansible validate-config -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/validate-config
}


upgrade
