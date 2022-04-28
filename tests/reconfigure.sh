#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function reconfigure {
    RAW_INVENTORY=/etc/kolla/inventory

    # TODO(jeffrey4l): make some configure file change and
    # trigger a real reconfigure
    kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks &> /tmp/logs/ansible/reconfigure-prechecks
    kolla-ansible -i ${RAW_INVENTORY} -vvv reconfigure &> /tmp/logs/ansible/reconfigure
}


reconfigure
