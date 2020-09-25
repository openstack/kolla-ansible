#!/bin/bash

# Test deployment of magnum, octavia and designate.

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

function test_designate {
    # Smoke test.
    openstack zone list --all

    # Create a default zone for fixed and floating IPs, then reconfigure nova
    # and neutron to use it.
    openstack zone create --email admin@example.org example.org.
    ZONE_ID=$(openstack zone show example.org. -f value -c id)

    mkdir -p /etc/kolla/config/designate/
    cat << EOF > /etc/kolla/config/designate/designate-sink.conf
[handler:nova_fixed]
zone_id = ${ZONE_ID}
[handler:neutron_floatingip]
zone_id = ${ZONE_ID}
EOF

    RAW_INVENTORY=/etc/kolla/inventory
    kolla-ansible -i ${RAW_INVENTORY} --tags designate -vvv reconfigure &> /tmp/logs/ansible/reconfigure-designate

    # Create an instance, and check that its name resolves.
    openstack server create --wait --image cirros --flavor m1.tiny --key-name mykey --network demo-net dns-test --wait
    attempt=1
    while true; do
        IP=$(dig +short @192.0.2.1 dns-test.example.org. A)
        if [[ -n $IP ]]; then
            break
        fi
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Failed to resolve dns-test.example.org."
            openstack recordset list ${ZONE_ID}
            exit 1
        fi
        sleep 10
    done
}

function test_magnum_logged {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate
    test_magnum_clusters
    test_octavia
    test_designate
}

function test_magnum {
    echo "Testing Magnum, Octavia and Designate"
    test_magnum_logged > /tmp/logs/ansible/test-magnum 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Magnum, Octavia and Designate failed. See ansible/test-magnum for details"
    else
        echo "Successfully tested Magnum, Octavia and Designate . See ansible/test-magnum for details"
    fi
    return $result
}

test_magnum
