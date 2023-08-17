#!/bin/bash

# Test deployment of octavia.

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function check_certificate_expiry {
    RAW_INVENTORY=/etc/kolla/inventory
    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate
    kolla-ansible octavia-certificates --check-expiry 7
    deactivate
}

function register_amphora_image {
    amphora_url=https://tarballs.opendev.org/openstack/octavia/test-images/test-only-amphora-x64-haproxy-ubuntu-focal.qcow2
    curl -o amphora.qcow2 $amphora_url
    (. /etc/kolla/octavia-openrc.sh && openstack image create amphora-x64-haproxy --file amphora.qcow2  --tag amphora --disk-format qcow2 --property hw_architecture='x86_64' --property hw_rng_model=virtio)
}

function test_octavia {
    register_amphora_image

    # Smoke test.
    openstack loadbalancer list

    # Create a Loadblanacer
    openstack loadbalancer create --name lb --vip-subnet-id demo-subnet --wait
    # Create a server to act as a backend.
    openstack server create --wait --image cirros --flavor m1.tiny --key-name mykey --network demo-net lb_member --wait
    member_fip=$(openstack floating ip create public1 -f value -c floating_ip_address)
    openstack server add floating ip lb_member ${member_fip}
    member_ip=$(openstack floating ip show ${member_fip} -f value -c fixed_ip_address)

    # Dummy HTTP server.
    attempts=12
    for i in $(seq 1 ${attempts}); do
        if ssh -v -o BatchMode=yes -o StrictHostKeyChecking=no cirros@${member_fip} 'nohup sh -c "while true; do echo -e \"HTTP/1.1 200 OK\n\n $(date)\" | sudo nc -l -p 8000; done &"'; then
            break
        elif [[ $i -eq ${attempts} ]]; then
            echo "Failed to access server via SSH after ${attempts} attempts"
            echo "Console log:"
            openstack console log show lb_member
            return 1
        else
            echo "Cannot access server - retrying"
        fi
        sleep 10
    done

    openstack loadbalancer listener create --name listener --protocol HTTP --protocol-port 8000 --wait lb
    openstack loadbalancer pool create --name pool --lb-algorithm ROUND_ROBIN --listener listener --protocol HTTP --wait
    openstack loadbalancer member create --subnet-id demo-subnet --address ${member_ip} --protocol-port 8000 pool --wait

    # Add a floating IP to the load balancer.
    lb_fip=$(openstack floating ip create public1 -f value -c name)
    lb_vip=$(openstack loadbalancer show lb -f value -c vip_address)
    lb_port_id=$(openstack port list --fixed-ip ip-address=$lb_vip -f value -c ID)
    openstack floating ip set $lb_fip --port $lb_port_id

    # Attempt to access the load balanced HTTP server.
    attempts=12
    for i in $(seq 1 ${attempts}); do
        if curl $lb_fip:8000; then
            break
        elif [[ $i -eq ${attempts} ]]; then
            echo "Failed to access load balanced service after ${attempts} attempts"
            return 1
        else
            echo "Cannot access load balancer - retrying"
        fi
        sleep 10
    done

    # Clean up.
    openstack loadbalancer delete lb --cascade --wait
    openstack floating ip delete ${lb_fip}

    openstack server remove floating ip lb_member ${member_fip}
    openstack floating ip delete ${member_fip}
    openstack server delete --wait lb_member
}

function test_octavia_logged {
    # Check if any certs expire within a week.
    check_certificate_expiry

    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate
    test_octavia
}

function test_octavia_setup {
    echo "Testing Octavia"
    test_octavia_logged > /tmp/logs/ansible/test-octavia 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Octavia failed. See ansible/test-octavia for details"
    else
        echo "Successfully tested Octavia. See ansible/test-octavia for details"
    fi
    return $result
}

test_octavia_setup

