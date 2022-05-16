#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function deploy {
    RAW_INVENTORY=/etc/kolla/inventory

    #TODO(inc0): Post-deploy complains that /etc/kolla is not writable. Probably we need to include become there
    sudo chmod -R 777 /etc/kolla
    # generate self-signed certificates for the optional internal TLS tests
    if [[ "$TLS_ENABLED" = "True" ]]; then
        kolla-ansible -i ${RAW_INVENTORY} -vvv certificates > /tmp/logs/ansible/certificates
    fi
    # Actually do the deployment
    kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks &> /tmp/logs/ansible/deploy-prechecks
    kolla-ansible -i ${RAW_INVENTORY} -vvv pull &> /tmp/logs/ansible/pull
    kolla-ansible -i ${RAW_INVENTORY} -vvv deploy &> /tmp/logs/ansible/deploy
    kolla-ansible -i ${RAW_INVENTORY} -vvv post-deploy &> /tmp/logs/ansible/post-deploy
}


deploy
