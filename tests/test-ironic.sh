#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function test_ironic_logged {
    # Assumes init-runonce has been executed.
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate

    echo "Enabling DHCP on the external (\"public\") subnet"
    openstack subnet set --dhcp public1-subnet

    # Smoke test ironic API.
    openstack baremetal driver list
    openstack baremetal node list
    openstack baremetal port list
    # Ironic Inspector API
    openstack baremetal introspection rule list

    openstack baremetal node show tk0
    openstack baremetal node power off tk0
    openstack baremetal node show tk0
    openstack baremetal node manage tk0
    openstack baremetal node show tk0
    openstack baremetal node provide tk0
    openstack baremetal node show tk0
    openstack baremetal node validate tk0

    echo "TESTING: Server creation"
    openstack server create --image cirros --flavor test-rc --key-name mykey --network public1 kolla_bm_boot_test
    local attempt
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
