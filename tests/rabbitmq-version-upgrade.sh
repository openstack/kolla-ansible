#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function rabbitmq-version-upgrade {
    RAW_INVENTORY=/etc/kolla/inventory

    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate

    kolla-ansible -i ${RAW_INVENTORY} -vvv rabbitmq-upgrade 3.12 &> /tmp/logs/ansible/rabbitmq-upgrade-3.12
    kolla-ansible -i ${RAW_INVENTORY} -vvv rabbitmq-upgrade 3.13 &> /tmp/logs/ansible/rabbitmq-upgrade-3.13
}


rabbitmq-version-upgrade
