#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

# Adapted from the function of the same name in the ironic devstack plugin.
function wait_for_placement_resources {
    # After nodes have been enrolled, we need to wait for both ironic and
    # nova's periodic tasks to populate the resource tracker with available
    # nodes and resources. Wait up to 2 minutes for a given resource before
    # timing out.
    local expected_count=1
    local resource_class="RC0"

    curl -L -o jq https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64
    chmod +x jq

    # TODO(mgoddard): switch to Placement OSC plugin, once it exists
    local token
    token=$(openstack token issue -f value -c id)
    local endpoint
    endpoint=$(openstack endpoint list --service placement --interface public -f value -c URL)
    if [[ -z $endpoint ]]; then
        echo "Cannot find Placement API endpoint"
        return 1
    fi

    local i
    local count
    echo "Waiting 2 minutes for Nova resource tracker to pick up $expected_count nodes"
    for i in $(seq 1 120); do
        # Fetch provider UUIDs from Placement
        local providers
        providers=$(curl -sH "X-Auth-Token: $token" $endpoint/resource_providers \
            | ./jq -r '.resource_providers[].uuid')

        local p
        # Total count of the resource class, has to be equal to nodes count
        count=0
        for p in $providers; do
            local amount
            # A resource class inventory record looks something like
            # {"max_unit": 1, "min_unit": 1, "step_size": 1, "reserved": 0, "total": 1, "allocation_ratio": 1}
            # Subtract reserved from total (defaulting both to 0)
            amount=$(curl -sH "X-Auth-Token: $token" $endpoint/resource_providers/$p/inventories \
                | ./jq ".inventories.CUSTOM_$resource_class as \$cls
                    | (\$cls.total // 0) - (\$cls.reserved // 0)")
            if [ $amount -gt 0 ]; then
                count=$(( count + $amount ))
            fi
        done

        if [ $count -ge $expected_count ]; then
            return 0
        fi
        sleep 1
    done

    echo "Timed out waiting for Nova to track $expected_count nodes"
    return 1
}

function create_resources {
    # Create a bare metal node and port.
    openstack baremetal node create \
        --name node-0 \
        --driver fake-hardware \
        --network-interface noop \
        --property cpu_arch=x86_64 \
        --resource-class rc0
    node_uuid=$(openstack baremetal node show node-0 -f value -c uuid)
    openstack baremetal port create \
        00:11:22:33:44:55 \
        --node $node_uuid
    openstack baremetal node power off node-0
    openstack baremetal node manage node-0 --wait
    openstack baremetal node provide node-0 --wait

    # Create a bare metal flavor in nova.
    openstack flavor create \
        baremetal \
        --vcpus 1 \
        --ram 1024 \
        --disk 10 \
        --property resources:CUSTOM_RC0=1 \
        --property resources:VCPU=0 \
        --property resources:MEMORY_MB=0 \
        --property resources:DISK_GB=0 \
        --public
}

function test_ironic_logged {
    # Assumes init-runonce has been executed.
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate

    # Smoke test ironic API.
    local baremetal_driver_list
    baremetal_driver_list=$(openstack baremetal driver list)
    openstack baremetal node list
    openstack baremetal port list

    # Sanity check.
    if ! echo "$baremetal_driver_list" | grep fake-hardware; then
        echo "No active conductors with fake-hardware driver"
        exit 1
    fi

    create_resources
    wait_for_placement_resources

    echo "TESTING: Server creation"
    openstack server create --wait --image cirros --flavor baremetal --key-name mykey --network demo-net kolla_boot_test
    openstack --debug server list
    # If the status is not ACTIVE, print info and exit 1
    if [[ $(openstack server show kolla_boot_test -f value -c status) != "ACTIVE" ]]; then
        echo "FAILED: Instance is not active"
        openstack --debug server show kolla_boot_test
        return 1
    fi
    echo "SUCCESS: Server creation"

    echo "TESTING: Server deletion"
    openstack server delete --wait kolla_boot_test
    echo "SUCCESS: Server deletion"
}

function test_ironic {
    echo "Testing Ironic"
    if ! test_ironic_logged > /tmp/logs/ansible/test-ironic 2>&1; then
        echo "Testing Ironic failed. See ansible/test-ironic for details"
        return 1
    else
        echo "Successfully tested Ironic. See ansible/test-ironic for details"
    fi
}

test_ironic
