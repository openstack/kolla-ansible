#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function upgrade {
    RAW_INVENTORY=/etc/kolla/inventory

    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate

    kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks &> /tmp/logs/ansible/upgrade-prechecks

    # NOTE(mattcrees): As om_enable_rabbitmq_quorum_queues now defaults to
    # true in Bobcat, we need to perform a migration to durable queues.
    # TODO(mattcrees): Remove these steps in Caracal.
    SERVICE_TAGS="heat,keystone,neutron,nova"
    if [[ $SCENARIO == "zun" ]] || [[ $SCENARIO == "cephadm" ]]; then
        SERVICE_TAGS+=",cinder"
    fi
    if [[ $SCENARIO == "scenario_nfv" ]]; then
        SERVICE_TAGS+=",barbican"
    fi
    if [[ $SCENARIO == "ironic" ]]; then
        SERVICE_TAGS+=",ironic"
    fi
    if [[ $SCENARIO == "masakari" ]]; then
        SERVICE_TAGS+=",masakari"
    fi
    if [[ $SCENARIO == "ovn" ]] || [[ $SCENARIO == "octavia" ]]; then
        SERVICE_TAGS+=",octavia"
    fi
    if [[ $SCENARIO == "magnum" ]]; then
        SERVICE_TAGS+=",magnum,designate"
    fi
    kolla-ansible -i ${RAW_INVENTORY} -vvv stop --tags $SERVICE_TAGS --yes-i-really-really-mean-it &> /tmp/logs/ansible/stop
    kolla-ansible -i ${RAW_INVENTORY} -vvv genconfig &> /tmp/logs/ansible/genconfig
    kolla-ansible -i ${RAW_INVENTORY} -vvv reconfigure --tags rabbitmq &> /tmp/logs/ansible/reconfigure-rabbitmq
    kolla-ansible -i ${RAW_INVENTORY} -vvv rabbitmq-reset-state &> /tmp/logs/ansible/rabbitmq-reset-state

    kolla-ansible -i ${RAW_INVENTORY} -vvv pull &> /tmp/logs/ansible/pull-upgrade
    kolla-ansible -i ${RAW_INVENTORY} -vvv upgrade &> /tmp/logs/ansible/upgrade

    kolla-ansible -i ${RAW_INVENTORY} -vvv post-deploy &> /tmp/logs/ansible/upgrade-post-deploy

    kolla-ansible -i ${RAW_INVENTORY} -vvv validate-config &> /tmp/logs/ansible/validate-config
}


upgrade
