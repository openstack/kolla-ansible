#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function upgrade {
    RAW_INVENTORY=/etc/kolla/inventory

    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate

    kolla-ansible certificates -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/certificates
    # Previous versions had older docker, requests requirements for example
    # Therefore we need to run bootstrap again to ensure libraries are in
    # proper versions (ansible-collection-kolla is different for new version, potentionally
    # also dependencies).
    kolla-ansible bootstrap-servers -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/upgrade-bootstrap
    # Skip rabbitmq-ha-precheck before the queues are migrated.
    kolla-ansible prechecks -i ${RAW_INVENTORY} --skip-tags rabbitmq-ha-precheck -vvv &> /tmp/logs/ansible/upgrade-prechecks-pre-rabbitmq

    # NOTE(SvenKieske): As om_enable_rabbitmq_transient_quorum_queue now also
    # enables quorum_queues for fanout/reply queues in Epoxy, we need
    # to perform a migration to durable queues.
    # TODO(SvenKieske): Remove these steps in F Cycle.
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
    kolla-ansible stop -i ${RAW_INVENTORY} -vvv --tags $SERVICE_TAGS --yes-i-really-really-mean-it --ignore-missing &> /tmp/logs/ansible/stop
    kolla-ansible genconfig -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/genconfig
    kolla-ansible rabbitmq-reset-state -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/rabbitmq-reset-state
    # Include rabbitmq-ha-precheck this time to confirm all queues have migrated.
    kolla-ansible prechecks -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/upgrade-prechecks

    kolla-ansible pull -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/pull-upgrade
    kolla-ansible upgrade -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/upgrade

    kolla-ansible post-deploy -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/upgrade-post-deploy

    kolla-ansible validate-config -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/validate-config
}


upgrade
