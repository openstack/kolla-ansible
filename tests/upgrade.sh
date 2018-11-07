#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function upgrade {
    RAW_INVENTORY=/etc/kolla/inventory

    # TODO(jeffrey4l): need run a real upgrade
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks > /tmp/logs/ansible/upgrade-prechecks
    # TODO(mgoddard): add pull action when we have a local registry service in
    # CI.
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv upgrade > /tmp/logs/ansible/upgrade
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv check > /tmp/logs/ansible/check-upgrade
}


upgrade
