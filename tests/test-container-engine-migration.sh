#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output
export PYTHONUNBUFFERED=1

VM_NAME="kolla_migration_test"
FIP_ADDR=

function create_instance {
    local name=$1
    local server_create_extra

    if [[ $IP_VERSION -eq 6 ]]; then
        # NOTE(yoctozepto): CirrOS has no IPv6 metadata support, hence need to use configdrive
        server_create_extra="${server_create_extra} --config-drive True"
    fi

    openstack server create --wait --image cirros --flavor c1.tiny --key-name mykey --network demo-net ${server_create_extra} ${name}
    # If the status is not ACTIVE, print info and exit 1
    if [[ $(openstack server show ${name} -f value -c status) != "ACTIVE" ]]; then
        echo "FAILED: Instance is not active"
        openstack --debug server show ${name}
        return 1
    fi
}

function start_instance {
    local name=$1
    local attempts
    attempts=12

    openstack server start ${name}

    # substitution for missing --wait argument
    for i in $(seq 1 ${attempts}); do
        if [[ $(openstack server show ${name} -f value -c status) == "ACTIVE" ]]; then
            break
        elif [[ $i -eq ${attempts} ]]; then
            echo "Failed to start server after ${attempts} attempts"
            echo "Console log:"
            openstack console log show ${name} || true
            openstack --debug server show ${name}
            return 1
        else
            echo "Server is not yet started - retrying"
        fi
        sleep 10
    done
}

function stop_instance {
    local name=$1
    local attempts
    attempts=12

    openstack server stop ${name}

    # substitution for missing --wait argument
    for i in $(seq 1 ${attempts}); do
        if [[ $(openstack server show ${name} -f value -c status) == "SHUTOFF" ]]; then
            break
        elif [[ $i -eq ${attempts} ]]; then
            echo "Failed to stop server after ${attempts} attempts"
            echo "Console log:"
            openstack console log show ${name} || true
            openstack --debug server show ${name}
            return 1
        else
            echo "Server is not yet stopped - retrying"
        fi
        sleep 10
    done
}

function delete_instance {
    local name=$1
    openstack server delete --wait ${name}
}

function create_fip {
    openstack floating ip create public1 -f value -c floating_ip_address
}

function delete_fip {
    local fip_addr=$1
    openstack floating ip delete ${fip_addr}
}

function attach_fip {
    local instance_name=$1
    local fip_addr=$2
    openstack server add floating ip ${instance_name} ${fip_addr}
}

function detach_fip {
    local instance_name=$1
    local fip_addr=$2
    openstack server remove floating ip ${instance_name} ${fip_addr}
}

function test_ssh {
    local instance_name=$1
    local fip_addr=$2
    local attempts
    attempts=12
    for i in $(seq 1 ${attempts}); do
        if ping -c1 -W1 ${fip_addr} && ssh -v -o BatchMode=yes -o StrictHostKeyChecking=no cirros@${fip_addr} hostname; then
            break
        elif [[ $i -eq ${attempts} ]]; then
            echo "Failed to access server via SSH after ${attempts} attempts"
            echo "Console log:"
            openstack console log show ${instance_name} || true
            openstack --debug server show ${instance_name}
            return 1
        else
            echo "Cannot access server - retrying"
        fi
        sleep 10
    done
}

function test_initial_vm {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate

    echo "TESTING: Initial server creation"
    create_instance ${VM_NAME}
    echo "SUCCESS: Initial server creation"

    if [[ $IP_VERSION -eq 4 ]]; then
        echo "TESTING: Floating ip allocation"
        FIP_ADDR=$(create_fip)
        attach_fip ${VM_NAME} ${FIP_ADDR}
        echo "SUCCESS: Floating ip allocation"
    else
        # NOTE(yoctozepto): Neutron has no IPv6 NAT support, hence no floating ip addresses
        local instance_addresses
        FIP_ADDR=$(openstack server show ${VM_NAME} -f yaml -c addresses|tail -1|cut -d- -f2)
    fi

    echo "TESTING: PING&SSH to initial instance"
    test_ssh ${VM_NAME} ${FIP_ADDR}
    echo "SUCCESS: PING&SSH to initial instance"

    echo "TESTING: Stopping the initial instance"
    stop_instance ${VM_NAME}
    echo "SUCCESS: Stopped the initial instance"
}

function test_migrated_vm {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate

    echo "TESTING: Starting the migrated instance"
    start_instance ${VM_NAME}
    echo "SUCCESS: Started the migrated instance"

    echo "TESTING: PING&SSH to migrated instance"
    test_ssh ${VM_NAME} ${FIP_ADDR}
    echo "SUCCESS: PING&SSH to migrated instance"

    if [[ $IP_VERSION -eq 4 ]]; then
        echo "TESTING: Floating ip deallocation"
        detach_fip ${VM_NAME} ${FIP_ADDR}
        delete_fip ${FIP_ADDR}
        echo "SUCCESS: Floating ip deallocation"
    fi

    echo "TESTING: Server deletion"
    delete_instance ${VM_NAME}
    echo "SUCCESS: Server deletion"
}

function migrate_container_engine {
    echo "MIGRATION: Migrating from Docker to Podman"
    sed -i "s/\(kolla_container_engine:\s*\).*/\1podman/" /etc/kolla/globals.yml
    RAW_INVENTORY=/etc/kolla/inventory
    source ${KOLLA_ANSIBLE_VENV_PATH}/bin/activate
    kolla-ansible migrate-container-engine -i ${RAW_INVENTORY} -vvv
    echo "SUCCESS: Migrated from Docker to Podman"
}

function test_container_engine_migration_logged {
    test_initial_vm
    migrate_container_engine
    test_migrated_vm
}

function test_container_engine_migration {
    echo "Testing container engine migration from Docker to Podman"
    test_container_engine_migration_logged > /tmp/logs/ansible/test-container-engine-migration 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing container engine migration failed. See ansible/test-container-engine-migration for details"
    else
        echo "Successfully tested container engine migration. See ansible/test-container-engine-migration for details"
    fi
    return $result
}

test_container_engine_migration
