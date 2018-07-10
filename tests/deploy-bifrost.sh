#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function deploy_bifrost {
    RAW_INVENTORY=/etc/kolla/inventory

    # TODO(mgoddard): run prechecks.
    # Deploy the bifrost container.
    # TODO(mgoddard): add pull action when we have a local registry service in
    # CI.
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv deploy-bifrost > /tmp/logs/ansible/deploy-bifrost
}


deploy_bifrost
