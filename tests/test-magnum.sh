#!/bin/bash

# Test deployment of magnum and octavia.

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function test_magnum_clusters {
    openstack coe cluster list
    openstack coe cluster template list
}

function test_octavia {
    openstack loadbalancer list
}

function test_magnum_logged {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate
    test_magnum_clusters
    test_octavia
}

function test_magnum {
    echo "Testing Magnum and Octavia"
    test_magnum_logged > /tmp/logs/ansible/test-magnum 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Magnum and Octavia failed. See ansible/test-magnum for details"
    else
        echo "Successfully tested Magnum and Octavia. See ansible/test-magnum for details"
    fi
    return $result
}

test_magnum
