#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function reconfigure {
    RAW_INVENTORY=/etc/kolla/inventory

    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate

    # TODO(jeffrey4l): make some configure file change and
    # trigger a real reconfigure
    # NOTE(mnasiadka): Remove OVN DB containers and volumes on primary to test recreation
    if [[ $SCENARIO == "ovn" ]]; then
        sudo ${CONTAINER_ENGINE} rm -f ovn_nb_db ovn_sb_db && sudo ${CONTAINER_ENGINE} volume rm ovn_nb_db ovn_sb_db
    fi
    kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks &> /tmp/logs/ansible/reconfigure-prechecks
    kolla-ansible -i ${RAW_INVENTORY} -vvv reconfigure &> /tmp/logs/ansible/reconfigure
}


reconfigure
