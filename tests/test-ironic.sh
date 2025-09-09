#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function test_ironic_logged {
    # Assumes init-runonce has been executed.
    KOLLA_CONFIG_PATH=${KOLLA_CONFIG_PATH:-/etc/kolla}
    export OS_CLIENT_CONFIG_FILE=${KOLLA_CONFIG_PATH}/clouds.yaml
    export OS_CLOUD=kolla-admin-internal
    . ~/openstackclient-venv/bin/activate

    echo "Enabling DHCP on the external (\"public\") subnet"
    openstack subnet set --dhcp public1-subnet

    # Smoke test ironic API.
    openstack --os-cloud kolla-admin-system-internal baremetal driver list
    openstack --os-cloud kolla-admin-system-internal baremetal node list
    openstack baremetal port list

    openstack baremetal node show tk0
    openstack baremetal node power off tk0
    openstack baremetal node show tk0
    openstack baremetal node manage tk0
    openstack baremetal node show tk0
    openstack baremetal node validate tk0

    echo "TESTING: Server inspection"
    openstack baremetal node inspect tk0
    local attempt
    attempt=1
    while [[ $(openstack baremetal node show tk0 -f value -c provision_state) != "manageable" ]]; do
        echo "Server not yet manageable, check $attempt - retrying"
        attempt=$((attempt+1))
        if [[ $attempt -eq 16 ]]; then
            echo "FAILED: Server did not finish inspection after $attempt checks"
            openstack baremetal node show tk0
            return 1
        fi
        sleep 60
    done
    openstack baremetal node inventory save tk0
    echo ""
    echo "SUCCESS: Server inspection"

    echo "TESTING: Server creation"
    openstack baremetal node provide tk0
    attempt=1
    while [[ $(openstack baremetal node show tk0 -f value -c provision_state) != "available" ]]; do
        echo "Server not yet available, check $attempt - retrying"
        attempt=$((attempt+1))
        if [[ $attempt -eq 16 ]]; then
            echo "FAILED: Server did not get to available state after $attempt checks"
            openstack baremetal node show tk0
            return 1
        fi
        sleep 60
    done
    # NOTE(mnasiadka): Wait for nova-compute-ironic to pick up the new node
    sleep 60
    openstack server create --image cirros --flavor test-rc --key-name mykey --network public1 kolla_bm_boot_test
    attempt=1
    while [[ $(openstack server show kolla_bm_boot_test -f value -c status) != "ACTIVE" ]]; do
        echo "Server not yet active, check $attempt - retrying"
        attempt=$((attempt+1))
        if [[ $attempt -eq 16 ]]; then
            echo "FAILED: Server did not become active after $attempt checks"
            openstack server show kolla_bm_boot_test
            return 1
        fi
        sleep 60
    done
    echo "SUCCESS: Server creation"

    echo "TESTING: Server deletion"
    openstack server delete --wait kolla_bm_boot_test
    echo "SUCCESS: Server deletion"
}

function test_ironic {
    echo "Testing Ironic"
    test_ironic_logged > /tmp/logs/ansible/test-ironic 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Ironic failed. See ansible/test-ironic for details"
    else
        echo "Successfully tested Ironic. See ansible/test-ironic for details"
    fi
    return $result
}

test_ironic
