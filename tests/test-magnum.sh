#!/bin/bash

# Test deployment of magnum, trove and designate.

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function test_magnum_clusters {
    openstack coe cluster list
    openstack coe cluster template list
}

function test_trove {
    # smoke test
    openstack database instance list
    openstack database cluster list
}

function check_if_resolvable {
    local dns_domain="${1}"
    local dns_record="${2}"
    local record_type="${3}"

    attempt=1
    while true; do
        IP=$(dig +short @192.0.2.1 ${dns_record} ${record_type})
        if [[ -n $IP ]]; then
            break
        fi
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "[e] Failed to resolve ${dns_record}"
            openstack recordset list ${dns_domain}
            exit 1
        fi
        sleep 10
    done
}

function test_designate {
    # Smoke test.
    openstack zone list --all

    SERVER_NAME="my_vm"
    SERVER_NAME_SANITIZED=$(echo ${SERVER_NAME} | sed -e 's/_/-/g')
    DNS_DOMAIN="floating.example.org."

    openstack zone create --email admin@example.org ${DNS_DOMAIN}

    openstack network create --dns-domain ${DNS_DOMAIN} tenant-dns-test
    openstack subnet create --subnet-range 192.168.99.0/24 --network tenant-dns-test tenant-dns-test

    openstack router create router-dns-test
    openstack router set --external-gateway public1 router-dns-test
    openstack router add subnet router-dns-test tenant-dns-test

    openstack server create --image cirros --flavor c1.tiny --network tenant-dns-test  ${SERVER_NAME}

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

    openstack floating ip create public1 --port ${PORT_ID}

    check_if_resolvable "${DNS_DOMAIN}" "${SERVER_NAME_SANITIZED}.${DNS_DOMAIN}" "A"

    FLOATING_IP_ID=$(openstack floating ip list --port ${PORT_ID} -f value -c ID)

    openstack server remove floating ip ${SERVER_ID} ${FLOATING_IP_ID}
    openstack floating ip delete ${FLOATING_IP_ID}
    openstack server delete --wait ${SERVER_ID}

    DNS_DOMAIN="floating-2.example.org."
    DNS_NAME="my-floatingip"
    ZONE_ID=$(openstack zone create --email admin@example.org ${DNS_DOMAIN} -f value -c id)
    FLOATING_IP_ID=$(openstack floating ip create --dns-domain ${DNS_DOMAIN} --dns-name ${DNS_NAME} public1 -f value -c id)

    check_if_resolvable "${DNS_DOMAIN}" "${DNS_NAME}.${DNS_DOMAIN}" "A"

    openstack floating ip delete ${FLOATING_IP_ID}
    openstack zone delete ${ZONE_ID}

    DNS_DOMAIN="fixed.example.org."
    DNS_NAME="port"
    ZONE_ID=$(openstack zone create --email admin@example.org ${DNS_DOMAIN} -f value -c id)

    SUBNET_ID=$(openstack subnet create --network public1 public1-subnet-ipv6 --ip-version 6 --subnet-range 2001:db8:42:42::/64 --dns-publish-fixed-ip -f value -c id)
    PORT_ID=$(openstack port create ${DNS_NAME} --dns-domain ${DNS_DOMAIN} --dns-name ${DNS_NAME} --network public1 -f value -c id)

    check_if_resolvable "${DNS_DOMAIN}" "${DNS_NAME}.${DNS_DOMAIN}" "AAAA"

    openstack port delete ${PORT_ID}

    DNS_DOMAIN="fixed.sink.example.org."
    openstack zone create --email admin@example.org ${DNS_DOMAIN}
    ZONE_ID_FIXED=$(openstack zone show ${DNS_DOMAIN} -f value -c id)

    DNS_DOMAIN="floating.sink.example.org."
    openstack zone create --email admin@example.org ${DNS_DOMAIN}
    ZONE_ID_FLOATING=$(openstack zone show ${DNS_DOMAIN} -f value -c id)

    mkdir -p /etc/kolla/config/designate/
    cat << EOF > /etc/kolla/config/designate/designate-sink.conf
[handler:nova_fixed]
zone_id = ${ZONE_ID_FIXED}
[handler:neutron_floatingip]
zone_id = ${ZONE_ID_FLOATING}
EOF

    RAW_INVENTORY=/etc/kolla/inventory
    deactivate
    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate
    echo 'designate_enable_notifications_sink: "yes"' >> /etc/kolla/globals.yml
    kolla-ansible reconfigure -i ${RAW_INVENTORY} --tags designate,nova,nova-cell,neutron -vvv &> /tmp/logs/ansible/reconfigure-designate
    deactivate
    source ~/openstackclient-venv/bin/activate

    DNS_DOMAIN="fixed.sink.example.org."
    SERVER_NAME="sink-server"
    openstack server create --image cirros --flavor c1.tiny --network tenant-dns-test ${SERVER_NAME}

    check_if_resolvable "${DNS_DOMAIN}" "${SERVER_NAME}.${DNS_DOMAIN}" "A"

    SERVER_ID=$(openstack server show ${SERVER_NAME} -f value -c id)

    FLOATING_IP_ID=$(openstack floating ip create public1 -f value -c id)

    DNS_DOMAIN="floating.sink.example.org."
    openstack server add floating ip ${SERVER_ID} ${FLOATING_IP_ID}
    FLOATING_IP_IP=$(openstack floating ip show ${FLOATING_IP_ID} -f value -c floating_ip_address)
    DNS_NAME_ASSIGNMENT=$(echo "${FLOATING_IP_IP}" | sed -e 's/\./-/g')

    check_if_resolvable "${DNS_DOMAIN}" "${DNS_NAME_ASSIGNMENT}.${DNS_DOMAIN}" "A"

    openstack server remove floating ip ${SERVER_ID} ${FLOATING_IP_ID}
    openstack server delete --wait ${SERVER_ID}
    openstack zone delete ${ZONE_ID_FIXED}
    openstack zone delete ${ZONE_ID_FLOATING}

    openstack zone delete floating.example.org.
}

function test_magnum_logged {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate
    test_magnum_clusters
    test_designate
    test_trove
}

function test_magnum {
    echo "Testing Magnum, Trove and Designate"
    test_magnum_logged > /tmp/logs/ansible/test-magnum 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Magnum, Trove and Designate failed. See ansible/test-magnum for details"
    else
        echo "Successfully tested Magnum, Trove and Designate . See ansible/test-magnum for details"
    fi
    return $result
}

test_magnum
