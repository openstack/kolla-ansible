#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function test_smoke {
    openstack --debug compute service list
    openstack --debug network agent list
    openstack --debug orchestration service list
    if [[ $SCENARIO == "ceph-ansible" ]] || [[ $SCENARIO == "zun" ]]; then
        openstack --debug volume service list
    fi
}

function test_instance_boot {
    echo "TESTING: Server creation"
    openstack server create --wait --image cirros --flavor m1.tiny --key-name mykey --network demo-net kolla_boot_test
    openstack --debug server list
    # If the status is not ACTIVE, print info and exit 1
    if [[ $(openstack server show kolla_boot_test -f value -c status) != "ACTIVE" ]]; then
        echo "FAILED: Instance is not active"
        openstack --debug server show kolla_boot_test
        return 1
    fi
    echo "SUCCESS: Server creation"

    if [[ $SCENARIO == "ceph-ansible" ]] || [[ $SCENARIO == "zun" ]]; then
        echo "TESTING: Cinder volume attachment"
        openstack volume create --size 2 test_volume
        attempt=1
        while [[ $(openstack volume show test_volume -f value -c status) != "available" ]]; do
            echo "Volume not available yet"
            attempt=$((attempt+1))
            if [[ $attempt -eq 10 ]]; then
                echo "Volume failed to become available"
                openstack volume show test_volume
                return 1
            fi
            sleep 10
        done
        openstack server add volume kolla_boot_test test_volume --device /dev/vdb
        attempt=1
        while [[ $(openstack volume show test_volume -f value -c status) != "in-use" ]]; do
            echo "Volume not attached yet"
            attempt=$((attempt+1))
            if [[ $attempt -eq 10 ]]; then
                echo "Volume failed to attach"
                openstack volume show test_volume
                return 1
            fi
            sleep 10
        done
        openstack server remove volume kolla_boot_test test_volume
        attempt=1
        while [[ $(openstack volume show test_volume -f value -c status) != "available" ]]; do
            echo "Volume not detached yet"
            attempt=$((attempt+1))
            if [[ $attempt -eq 10 ]]; then
                echo "Volume failed to detach"
                openstack volume show test_volume
                return 1
            fi
            sleep 10
        done
        openstack volume delete test_volume
        echo "SUCCESS: Cinder volume attachment"
    fi

    echo "TESTING: Floating ip allocation"
    fip_addr=$(openstack floating ip create public1 -f value -c floating_ip_address)
    openstack server add floating ip kolla_boot_test ${fip_addr}
    echo "SUCCESS: Floating ip allocation"

    echo "TESTING: PING&SSH to floating ip"
    attempts=12
    for i in $(seq 1 ${attempts}); do
        if ping -c1 -W1 ${fip_addr} && ssh -v -o BatchMode=yes -o StrictHostKeyChecking=no cirros@${fip_addr} hostname; then
            break
        elif [[ $i -eq ${attempts} ]]; then
            echo "Failed to access server via SSH after ${attempts} attempts"
            echo "Console log:"
            openstack console log show kolla_boot_test
            return 1
        else
            echo "Cannot access server - retrying"
        fi
        sleep 10
    done
    echo "SUCCESS: PING&SSH to floating ip"

    echo "TESTING: Floating ip deallocation"
    openstack server remove floating ip kolla_boot_test ${fip_addr}
    openstack floating ip delete ${fip_addr}
    echo "SUCCESS: Floating ip deallocation"

    echo "TESTING: Server deletion"
    openstack server delete --wait kolla_boot_test
    echo "SUCCESS: Server deletion"
}

function test_openstack_logged {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate
    test_smoke
    test_instance_boot
}

function test_openstack {
    echo "Testing OpenStack"
    log_file=/tmp/logs/ansible/test-core-openstack
    if [[ -f $log_file ]]; then
        log_file=${log_file}-upgrade
    fi
    test_openstack_logged > $log_file 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing OpenStack failed. See ansible/test-core-openstack for details"
    else
        echo "Successfully tested OpenStack. See ansible/test-core-openstack for details"
    fi
    return $result
}

test_openstack
