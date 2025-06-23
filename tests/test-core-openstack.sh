#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function test_smoke {
    openstack --debug endpoint list
    openstack --debug compute service list
    openstack --debug network agent list
    openstack --debug orchestration service list
    if [[ $SCENARIO == "cephadm" ]] || [[ $SCENARIO == "zun" ]]; then
        openstack --debug volume service list
    fi
}

function create_a_volume {
    local volume_name=$1

    local attempt

    openstack volume create --size 1 $volume_name
    attempt=1
    while [[ $(openstack volume show $volume_name -f value -c status) != "available" ]]; do
        echo "Volume $volume_name not available yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Volume $volume_name failed to become available"
            openstack volume show $volume_name
            return 1
        fi
        sleep 10
    done
}

function create_a_volume_from_image {
    local volume_name=$1
    local image_name=$2

    local attempt

    openstack volume create --image $image_name --size 1 $volume_name
    attempt=1
    while [[ $(openstack volume show $volume_name -f value -c status) != "available" ]]; do
        echo "Volume $volume_name not available yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 11 ]]; then
            echo "Volume $volume_name failed to become available"
            openstack volume show $volume_name
            return 1
        fi
        sleep 30
    done
}

function create_an_image_from_volume {
    local image_name=$1
    local volume_name=$2

    local attempt

    # NOTE(yoctozepto): Adding explicit microversion of Victoria as a sane default to work
    # around the bug: https://storyboard.openstack.org/#!/story/2009287
    openstack --os-volume-api-version 3.62 image create --volume $volume_name $image_name
    attempt=1
    while [[ $(openstack image show $image_name -f value -c status) != "active" ]]; do
        echo "Image $image_name not active yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 11 ]]; then
            echo "Image $image_name failed to become active"
            openstack image show $image_name
            return 1
        fi
        sleep 30
    done
}

function create_an_image_from_instance {
    local image_name=$1
    local instance_name=$2

    local attempt

    openstack server image create $instance_name --name $image_name
    attempt=1
    while [[ $(openstack image show $image_name -f value -c status) != "active" ]]; do
        echo "Image $image_name not active yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 11 ]]; then
            echo "Image $image_name failed to become active"
            openstack image show $image_name
            return 1
        fi
        sleep 30
    done
}

function attach_and_detach_a_volume {
    local volume_name=$1
    local instance_name=$2

    local attempt

    openstack server add volume $instance_name $volume_name --device /dev/vdb
    attempt=1
    while [[ $(openstack volume show $volume_name -f value -c status) != "in-use" ]]; do
        echo "Volume $volume_name not attached yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Volume failed to attach"
            openstack volume show $volume_name
            return 1
        fi
        sleep 10
    done

    openstack server remove volume $instance_name $volume_name
    attempt=1
    while [[ $(openstack volume show $volume_name -f value -c status) != "available" ]]; do
        echo "Volume $volume_name not detached yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Volume failed to detach"
            openstack volume show $volume_name
            return 1
        fi
        sleep 10
    done
}

function delete_a_volume {
    local volume_name=$1

    local attempt
    local result

    openstack volume delete $volume_name

    attempt=1
    # NOTE(yoctozepto): This is executed outside of the `while` clause
    # *on purpose*. You see, bash is evil (TM) and will silence any error
    # happening in any "condition" clause (such as `if` or `while`) even with
    # `errexit` being set.
    result=$(openstack volume list --name $volume_name -f value -c ID)
    while [[ -n "$result" ]]; do
        echo "Volume $volume_name not deleted yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Volume failed to delete"
            openstack volume show $volume_name
            return 1
        fi
        sleep 10
        result=$(openstack volume list --name $volume_name -f value -c ID)
    done
}

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

function resize_instance {
    local name=$1

    openstack server resize --flavor c2.tiny --wait ${name}
    # If the status is not VERIFY_RESIZE, print info and exit 1
    if [[ $(openstack server show ${name} -f value -c status) != "VERIFY_RESIZE" ]]; then
        echo "FAILED: Instance is not resized"
        openstack --debug server show ${name}
        return 1
    fi

    openstack server resize confirm ${name}

    # Confirming the resize operation is not instantaneous. Wait for change to
    # be reflected in server status.
    local attempt
    attempt=1
    while [[ $(openstack server show ${name} -f value -c status) != "ACTIVE" ]]; do
        echo "Instance is not active yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "FAILED: Instance failed to become active after resize confirm"
            openstack --debug server show ${name}
            return 1
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

function set_cirros_image_q35_machine_type {
    openstack image set --property hw_machine_type=q35 cirros
}

function unset_cirros_image_q35_machine_type {
    openstack image unset --property hw_machine_type cirros
}

function test_neutron_modules {
    # Exit the function if scenario is "ovn" or if there's an upgrade
    # as it only concerns ml2/ovs
    if [[ $SCENARIO == "ovn" ]] || [[ $HAS_UPGRADE == "yes" ]]; then
        return
    fi

    local modules
    modules=( $(sed -n '/neutron_modules_extra:/,/^[^ ]/p' /etc/kolla/globals.yml | grep -oP '^  - name: \K[^ ]+' | tr -d "'") )
    for module in "${modules[@]}"; do
        if ! grep -q "^${module} " /proc/modules; then
            echo "Error: Module $module is not loaded."
            exit 1
        else
            echo "Module $module is loaded."
        fi
    done
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

function test_instance_boot {
    local fip_addr
    local machine_type="${1}"
    local fip_file="/tmp/kolla_ci_pre_upgrade_fip_addr${machine_type:+_$machine_type}"
    local upgrade_instance_name="kolla_upgrade_test${machine_type:+_$machine_type}"
    local volume_name="durable_volume${machine_type:+_$machine_type}"

    echo "TESTING: Server creation"
    create_instance kolla_boot_test
    echo "SUCCESS: Server creation"

    if [[ $SCENARIO == "cephadm" ]] || [[ $SCENARIO == "zun" ]]; then
        echo "TESTING: Cinder volume creation and attachment"

        create_a_volume test_volume
        openstack volume show test_volume
        attach_and_detach_a_volume test_volume kolla_boot_test
        delete_a_volume test_volume

        # test a qcow2 image (non-cloneable)
        create_a_volume_from_image test_volume_from_image cirros
        openstack volume show test_volume_from_image
        attach_and_detach_a_volume test_volume_from_image kolla_boot_test
        delete_a_volume test_volume_from_image

        # test a raw image (cloneable)
        openstack image create --disk-format raw --container-format bare --public \
            --file /etc/passwd raw-image
        create_a_volume_from_image test_volume_from_image raw-image
        openstack volume show test_volume_from_image
        attach_and_detach_a_volume test_volume_from_image kolla_boot_test
        delete_a_volume test_volume_from_image
        openstack image delete raw-image

        echo "SUCCESS: Cinder volume creation and attachment"

        if [[ $HAS_UPGRADE == 'yes' ]]; then
            echo "TESTING: Cinder volume upgrade stability (PHASE: $PHASE)"

            if [[ $PHASE == 'deploy' ]]; then
                create_a_volume $volume_name
                openstack volume show $volume_name
            elif [[ $PHASE == 'upgrade' ]]; then
                openstack volume show $volume_name
                attach_and_detach_a_volume $volume_name kolla_boot_test
                delete_a_volume $volume_name
            fi

            echo "SUCCESS: Cinder volume upgrade stability (PHASE: $PHASE)"
        fi

        echo "TESTING: Glance image from Cinder volume and back to volume"

        create_a_volume test_volume_to_image
        openstack volume show test_volume_to_image
        create_an_image_from_volume test_image_from_volume test_volume_to_image

        create_a_volume_from_image test_volume_from_image_from_volume test_image_from_volume
        openstack volume show test_volume_from_image_from_volume
        attach_and_detach_a_volume test_volume_from_image_from_volume kolla_boot_test

        delete_a_volume test_volume_from_image_from_volume
        openstack image delete test_image_from_volume
        delete_a_volume test_volume_to_image

        echo "SUCCESS: Glance image from Cinder volume and back to volume"
    fi

    echo "TESTING: Instance image upload"
    create_an_image_from_instance image_from_instance kolla_boot_test
    openstack image delete image_from_instance
    echo "SUCCESS: Instance image upload"

    if [[ $IP_VERSION -eq 4 ]]; then
        echo "TESTING: Floating ip allocation"
        fip_addr=$(create_fip)
        attach_fip kolla_boot_test ${fip_addr}
        echo "SUCCESS: Floating ip allocation"
    else
        # NOTE(yoctozepto): Neutron has no IPv6 NAT support, hence no floating ip addresses
        local instance_addresses
        fip_addr=$(openstack server show kolla_boot_test -f yaml -c addresses|tail -1|cut -d- -f2)
    fi

    echo "TESTING: PING&SSH to instance"
    test_ssh kolla_boot_test ${fip_addr}
    echo "SUCCESS: PING&SSH to instance"

    if [[ $IP_VERSION -eq 4 ]]; then
        echo "TESTING: Floating ip deallocation"
        detach_fip kolla_boot_test ${fip_addr}
        delete_fip ${fip_addr}
        echo "SUCCESS: Floating ip deallocation"
    fi

    echo "TESTING: Server resize"
    resize_instance kolla_boot_test
    echo "SUCCESS: Server resize"

    echo "TESTING: Server deletion"
    delete_instance kolla_boot_test
    echo "SUCCESS: Server deletion"

    if [[ $HAS_UPGRADE == 'yes' ]]; then
        echo "TESTING: Instance (Nova and Neutron) upgrade stability (PHASE: $PHASE)"

        if [[ $PHASE == 'deploy' ]]; then
            create_instance $upgrade_instance_name
            fip_addr=$(create_fip)
            attach_fip $upgrade_instance_name ${fip_addr}
            test_ssh $upgrade_instance_name ${fip_addr}  # tested to see if the instance has not just failed booting already
            echo ${fip_addr} > $fip_file
        elif [[ $PHASE == 'upgrade' ]]; then
            fip_addr=$(cat $fip_file)
            test_ssh $upgrade_instance_name ${fip_addr}
            detach_fip $upgrade_instance_name ${fip_addr}
            delete_fip ${fip_addr}
            delete_instance $upgrade_instance_name
        fi

        echo "SUCCESS: Instance (Nova and Neutron) upgrade stability (PHASE: $PHASE)"
    fi
}

function test_internal_dns_integration {

    # As per test globals - neutron integration is turned off
    if openstack extension list --network -f value -c Alias | grep -q dns-integration; then
        DNS_NAME="my-port"
        PORT_NAME="${DNS_NAME}"
        DNS_DOMAIN=$(awk -F ':' '/neutron_dns_domain:/ { print $2 }' /etc/kolla/globals.yml \
                    | sed -e 's/"//g' -e "s/'//g" -e "s/\ *//g")

        openstack network create dns-test-network
        openstack subnet create --network dns-test-network --subnet-range 192.168.88.0/24 dns-test-subnet
        openstack port create --network dns-test-network --dns-name ${DNS_NAME} ${PORT_NAME}

        DNS_ASSIGNMENT=$(openstack port show ${DNS_NAME} -f json -c dns_assignment)
        FQDN=$(echo ${DNS_ASSIGNMENT} | python -c 'import json,sys;obj=json.load(sys.stdin);print(obj["dns_assignment"][0]["fqdn"]);')
        HOSTNAME=$(echo ${DNS_ASSIGNMENT} | python -c 'import json,sys;obj=json.load(sys.stdin);print(obj["dns_assignment"][0]["hostname"]);')

        if [ "${DNS_NAME}.${DNS_DOMAIN}" == "${FQDN}" ]; then
            echo "[i] Test neutron internal DNS integration FQDN check port - PASS"
        else
            echo "[e] Test neutron internal DNS integration FQDN check port - FAIL"
            exit 1
        fi

        if [ "${DNS_NAME}" == "${HOSTNAME}" ]; then
            echo "[i] Test neutron internal DNS integration HOSTNAME check port - PASS"
        else
            echo "[e] Test neutron internal DNS integration HOSTNAME check port - FAIL"
            exit 1
        fi

        openstack port delete ${PORT_NAME}

        SERVER_NAME="my_vm"
        SERVER_NAME_SANITIZED=$(echo ${SERVER_NAME} | sed -e 's/_/-/g')

        openstack server create --image cirros --flavor c1.tiny --network dns-test-network ${SERVER_NAME}

        SERVER_ID=$(openstack server show ${SERVER_NAME} -f value -c id)
        attempt=0
        while [[ -z $(openstack port list --device-id ${SERVER_ID} -f value -c ID) ]]; do
            echo "Port for server ${SERVER_NAME} not available yet"
            attempt=$((attempt+1))
            if [[ $attempt -eq 10 ]]; then
                echo "ERROR: Port for server ${SERVER_NAME} failed to become available"
                openstack port list --device-id ${SERVER_ID}
                return 1
            fi
            sleep $attempt
        done
        PORT_ID=$(openstack port list --device-id ${SERVER_ID} -f value -c ID)

        DNS_ASSIGNMENT=$(openstack port show ${PORT_ID} -f json -c dns_assignment)
        FQDN=$(echo ${DNS_ASSIGNMENT} | python -c 'import json,sys;obj=json.load(sys.stdin);print(obj["dns_assignment"][0]["fqdn"]);')
        HOSTNAME=$(echo ${DNS_ASSIGNMENT} | python -c 'import json,sys;obj=json.load(sys.stdin);print(obj["dns_assignment"][0]["hostname"]);')

        if [ "${SERVER_NAME_SANITIZED}.${DNS_DOMAIN}" == "${FQDN}" ]; then
            echo "[i] Test neutron internal DNS integration FQDN check instance create - PASS"
        else
            echo "[e] Test neutron internal DNS integration FQDN check instance create - FAIL"
            exit 1
        fi

        if [ "${SERVER_NAME_SANITIZED}" == "${HOSTNAME}" ]; then
            echo "[i] Test neutron internal DNS integration HOSTNAME check instance create - PASS"
        else
            echo "[e] Test neutron internal DNS integration HOSTNAME check instance create - FAIL"
            exit 1
        fi

        openstack server delete --wait ${SERVER_NAME}
        openstack subnet delete dns-test-subnet
        openstack network delete dns-test-network

    else
        echo "[i] DNS Integration is not enabled."
    fi
}

function test_proxysql_prometheus_exporter {
    if [[ $SCENARIO == "cells" ]]; then
        if curl -v http://127.0.0.1:6070/metrics 2>/dev/null | grep '^proxysql_'; then
            echo "[i] Proxysql prometheus exporter - PASS"
            mkdir -p /tmp/logs/prometheus-exporters/proxysql
            curl -v http://127.0.0.1:6070/metrics 2>/dev/null -o /tmp/logs/prometheus-exporters/proxysql/exporter.txt
        else
            echo "[e] Proxysql prometheus exporter - FAIL"
            exit 1
        fi
    fi
}

function test_openstack_logged {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate
    test_smoke
    test_neutron_modules
    test_instance_boot
    test_internal_dns_integration
    test_proxysql_prometheus_exporter

    # Check for x86_64 architecture to run q35 tests
    if [[ $(uname -m) == "x86_64" ]]; then
        set_cirros_image_q35_machine_type
        test_instance_boot q35
        unset_cirros_image_q35_machine_type
    fi
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
