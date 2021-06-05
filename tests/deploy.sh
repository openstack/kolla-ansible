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
    kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks &> /tmp/logs/ansible/deploy-prechecks
    kolla-ansible -i ${RAW_INVENTORY} -vvv pull &> /tmp/logs/ansible/pull
    kolla-ansible -i ${RAW_INVENTORY} -vvv deploy &> /tmp/logs/ansible/deploy
    kolla-ansible -i ${RAW_INVENTORY} -vvv post-deploy &> /tmp/logs/ansible/post-deploy
    kolla-ansible -i ${RAW_INVENTORY} -vvv check &> /tmp/logs/ansible/check-deploy
}


deploy
