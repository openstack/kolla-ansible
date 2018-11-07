#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function upgrade_bifrost {
    RAW_INVENTORY=/etc/kolla/inventory

    # TODO(mgoddard): run prechecks.
    # TODO(mgoddard): add pull action when we have a local registry service in
    # CI.
    # TODO(mgoddard): make some configuration file changes and trigger a real
    # upgrade.
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv deploy-bifrost >  /tmp/logs/ansible/upgrade-bifrost
}


upgrade_bifrost
