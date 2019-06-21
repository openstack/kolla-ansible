#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function upgrade {
    RAW_INVENTORY=/etc/kolla/inventory

    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks &> /tmp/logs/ansible/upgrade-prechecks
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv pull &> /tmp/logs/ansible/pull-upgrade
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv upgrade &> /tmp/logs/ansible/upgrade
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv check &> /tmp/logs/ansible/check-upgrade
}


upgrade
