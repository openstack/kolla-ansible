#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function deploy {
    RAW_INVENTORY=/etc/kolla/inventory

    # Create dummy interface for neutron
    ansible -m shell -i ${RAW_INVENTORY} -b -a "ip l a fake_interface type dummy" all

    #TODO(inc0): Post-deploy complains that /etc/kolla is not writable. Probably we need to include become there
    sudo chmod -R 777 /etc/kolla
    # Actually do the deployment
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks > /tmp/logs/ansible/deploy-prechecks
    # TODO(jeffrey4l): add pull action when we have a local registry
    # service in CI
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv deploy > /tmp/logs/ansible/deploy
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv post-deploy > /tmp/logs/ansible/post-deploy
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv check > /tmp/logs/ansible/check-deploy
    . /etc/kolla/admin-openrc.sh
    # Wait for service ready
    sleep 15

    if ! openstack image show cirros >/dev/null 2>&1; then
        echo "Initialising OpenStack resources via init-runonce"
        tools/init-runonce
    else
        echo "Not running init-runonce - resources exist"
    fi
}


deploy
