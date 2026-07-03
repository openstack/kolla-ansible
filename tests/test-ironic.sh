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

    for node_name in tk0 tk1; do
        openstack baremetal node show $node_name
        openstack baremetal node power off $node_name
        openstack baremetal node show $node_name
        openstack baremetal node manage $node_name
        openstack baremetal node show $node_name
        openstack baremetal node validate $node_name
    done

    echo "TESTING: Server inspection"
    for node_name in tk0 tk1; do
        openstack baremetal node inspect $node_name
        local attempt
        attempt=1
        while [[ $(openstack baremetal node show $node_name -f value -c provision_state) != "manageable" ]]; do
            echo "Server not yet manageable, check $attempt - retrying"
            attempt=$((attempt+1))
            if [[ $attempt -eq 16 ]]; then
                echo "FAILED: Server did not finish inspection after $attempt checks"
                openstack baremetal node show $node_name
                return 1
            fi
            sleep 60
        done
        openstack baremetal node inventory save $node_name
    done
    echo ""
    echo "SUCCESS: Server inspection"

    echo "TESTING: Server creation"
    for node_name in tk0 tk1; do
        openstack baremetal node provide $node_name
        attempt=1
        while [[ $(openstack baremetal node show $node_name -f value -c provision_state) != "available" ]]; do
            echo "Server not yet available, check $attempt - retrying"
            attempt=$((attempt+1))
            if [[ $attempt -eq 16 ]]; then
                echo "FAILED: Server did not get to available state after $attempt checks"
                openstack baremetal node show $node_name
                return 1
            fi
            sleep 60
        done
    done
    # NOTE(mnasiadka): Wait for nova-compute-ironic to pick up the new node
    sleep 60
    for suffix in "" -red; do
        flavor_name="test-rc$suffix"
        server_name="kolla_bm_boot_test$suffix"
        openstack server create --image cirros --flavor $flavor_name --key-name mykey --network public1 $server_name
        attempt=1
        while [[ $(openstack server show $server_name -f value -c status) != "ACTIVE" ]]; do
            echo "Server not yet active, check $attempt - retrying"
            attempt=$((attempt+1))
            if [[ $attempt -eq 20 ]]; then
                echo "FAILED: Server did not become active after $attempt checks"
                openstack server show $server_name
                return 1
            fi
            sleep 60
        done
    done
    echo "SUCCESS: Server creation"

    echo "TESTING: Server deletion"
    openstack server delete --wait kolla_bm_boot_test
    openstack server delete --wait kolla_bm_boot_test-red
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
