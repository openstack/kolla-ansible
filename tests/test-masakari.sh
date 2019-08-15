#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function test_masakari_logged {

    # Source OpenStack credentials
    . /etc/kolla/admin-openrc.sh

    # Activate virtualenv to access Masakari client
    . ~/openstackclient-venv/bin/activate

    # NOTE:(gtrellu) Masakari client/API has a bug which generate a mismatch
    # between what the client send and what the API should received.
    CLIENT_OPTS="--os-ha-api-version 1.0"

    # Get the first Nova compute
    if ! HYPERVISOR=$(openstack hypervisor list -f value -c 'Hypervisor Hostname' | head -n1); then
        echo "Unable to get Nova hypervisor list"
        return 1
    fi

    # Create Masakari segment
    if ! openstack $CLIENT_OPTS segment create test_segment auto COMPUTE; then
        echo "Unable to create Masakari segment"
        return 1
    fi

    # Add Nova compute to Masakari segment
    if ! openstack $CLIENT_OPTS segment host create $HYPERVISOR COMPUTE SSH test_segment; then
        echo "Unable to add Nova hypervisor to Masakari segment"
        return 1
    fi

    # Delete Masakari segment
    if ! openstack $CLIENT_OPTS segment delete test_segment; then
        echo "Unable to delete Masakari segment"
        return 1
    fi

    # Exit virtualenv
    deactivate
}

function test_masakari {
    echo "Testing Masakari"
    test_masakari_logged > /tmp/logs/ansible/test-masakari 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Masakari failed. See ansible/test-masakari for details"
    else
        echo "Successfully tested Masakari. See ansible/test-masakari for details"
    fi
    return $result
}

test_masakari
