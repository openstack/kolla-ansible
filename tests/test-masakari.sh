#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function test_hacluster_logged {
    container_engine="${1:-docker}"
    local cluster_failure
    cluster_failure=0

    # NOTE(yoctozepto): repeated -V in commands below is used to get 'debug'
    # output; the right amount differs between command sets; the next level is
    # 'trace' which is overly verbose; PCMK_debug=no is used to revert the env
    # var setting from the container which would cause these commands to log up
    # to 'trace' (likely a pacemaker bug)

    if ! sudo ${container_engine} exec hacluster_pacemaker cibadmin -VVVVVV --query --local; then
        cluster_failure=1
    fi

    local mon_output

    if ! mon_output=$(sudo ${container_engine} exec -e PCMK_debug=no hacluster_pacemaker crm_mon -VVVVV --one-shot); then
        cluster_failure=1
    fi

    if ! sudo ${container_engine} exec -e PCMK_debug=no hacluster_pacemaker crm_verify -VVVVV --live-check; then
        cluster_failure=1
    fi

    # NOTE(yoctozepto): crm_mon output should include:
    #   * Online: [ primary secondary ]
    #   * RemoteOnline: [ ternary1 ternary2 ]

    if ! echo "$mon_output" | grep 'Online: \[ primary secondary \]'; then
        echo 'Full members missing' >&2
        cluster_failure=1
    fi

    if ! echo "$mon_output" | grep 'RemoteOnline: \[ ternary1 ternary2 \]'; then
        echo 'Remote members missing' >&2
        cluster_failure=1
    fi

    if [[ $cluster_failure -eq 1 ]]; then
        echo "HAcluster failed"
        return 1
    else
        echo "HAcluster healthy"
    fi
}

function test_masakari_logged {
    # Source OpenStack credentials
    . /etc/kolla/admin-openrc.sh

    # Activate virtualenv to access Masakari client
    . ~/openstackclient-venv/bin/activate

    # Create Masakari segment
    if ! openstack segment create test_segment auto COMPUTE; then
        echo "Unable to create Masakari segment"
        return 1
    fi

    openstack segment host create ternary1 COMPUTE SSH test_segment
    openstack segment host create ternary2 COMPUTE SSH test_segment

    # Delete Masakari segment
    if ! openstack segment delete test_segment; then
        echo "Unable to delete Masakari segment"
        return 1
    fi

    # Exit virtualenv
    deactivate
}

function test_masakari {
    echo "Testing Masakari"
    test_hacluster_logged $1 > /tmp/logs/ansible/test-hacluster 2>&1
    test_masakari_logged > /tmp/logs/ansible/test-masakari 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Masakari failed. See ansible/test-masakari for details"
    else
        echo "Successfully tested Masakari. See ansible/test-masakari for details"
    fi
    return $result
}

test_masakari $1
