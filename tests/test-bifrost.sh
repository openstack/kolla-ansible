#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function test_bifrost {
    # TODO(mgoddard): More testing, deploy bare metal nodes.
    # TODO(mgoddard): Use openstackclient when clouds.yaml works. See
    # https://bugs.launchpad.net/bifrost/+bug/1754070.
    attempts=0
    while [[ $(sudo docker exec bifrost_deploy bash -c "OS_CLOUD=bifrost openstack baremetal driver list -f value" | wc -l) -eq 0 ]]; do
        attempts=$((attempts + 1))
        if [[ $attempts -gt 6 ]]; then
            echo "Timed out waiting for ironic conductor to become active"
            exit 1
        fi
        sleep 10
    done
    sudo docker exec bifrost_deploy bash -c "OS_CLOUD=bifrost openstack baremetal node list"
    sudo docker exec bifrost_deploy bash -c "OS_CLOUD=bifrost openstack baremetal node create --driver ipmi --name test-node"
    sudo docker exec bifrost_deploy bash -c "OS_CLOUD=bifrost openstack baremetal node delete test-node"
}


test_bifrost
