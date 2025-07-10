#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output
export PYTHONUNBUFFERED=1

function test_ovn {
    # NOTE(yoctozepto): could use real ini parsing but this is fine for now
    local neutron_ml2_conf_path=/etc/kolla/neutron-server/ml2_conf.ini
    ovn_nb_connection=$(sudo grep -P -o -e "(?<=^ovn_nb_connection = ).*" "$neutron_ml2_conf_path")
    ovn_sb_connection=$(sudo grep -P -o -e "(?<=^ovn_sb_connection = ).*" "$neutron_ml2_conf_path")

    # List OVN NB/SB entries
    echo "OVN NB DB entries:"
    # TODO(mnasiadka): Remove the first part of conditional in G cycle
    if [ $IS_UPGRADE == "yes" ]; then
        sudo ${container_engine} exec ovn_northd ovn-nbctl --db "$ovn_nb_connection" show
    else
        sudo ${container_engine} exec ovn_northd ovn-nbctl show
    fi

    echo "OVN SB DB entries:"
    # TODO(mnasiadka): Remove the first part of conditional in G cycle
    if [ $IS_UPGRADE == "yes" ]; then
        sudo ${container_engine} exec ovn_northd ovn-sbctl --db "$ovn_sb_connection" show
    else
        sudo ${container_engine} exec ovn_northd ovn-sbctl show
    fi

    OVNNB_STATUS=$(sudo ${container_engine} exec ovn_nb_db ovs-appctl -t /var/run/ovn/ovnnb_db.ctl cluster/status OVN_Northbound)
    OVNSB_STATUS=$(sudo ${container_engine} exec ovn_sb_db ovs-appctl -t /var/run/ovn/ovnsb_db.ctl cluster/status OVN_Southbound)

    if [[ $(grep -o "at tcp:" <<< ${OVNNB_STATUS} | wc -l) != "3" ]]; then
        echo "ERR: NB Cluster does not have 3 nodes"
        echo "Output: ${OVNNB_STATUS}"
        exit 1
    fi

    if [[ $(grep -o "at tcp:" <<< ${OVNSB_STATUS} | wc -l) != "3" ]]; then
        echo "ERR: SB Cluster does not have 3 nodes"
        echo "Output: ${OVNSB_STATUS}"
        exit 1
    fi

    echo "OVS entries"
    sudo ${container_engine} exec openvswitch_vswitchd ovs-vsctl list open
}

function test_octavia {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate
    echo "Testing OVN Octavia provider"
    echo "Smoke test"
    openstack loadbalancer list

    # Create a server to act as a backend
    openstack server create --wait --image cirros --flavor c1.tiny --key-name mykey --network demo-net lb_member --wait
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

    echo "Creating Octavia OVN LB:"
    openstack loadbalancer create --vip-network-id demo-net --provider ovn --name test_ovn_lb --wait
    openstack loadbalancer listener create --protocol TCP --protocol-port 8000 --name test_ovn_lb_listener --wait test_ovn_lb
    openstack loadbalancer pool create --protocol TCP --lb-algorithm SOURCE_IP_PORT --listener test_ovn_lb_listener --name test_ovn_lb_pool --wait
    subnet_id=$(openstack subnet list -c ID -f value --name demo-subnet)
    openstack loadbalancer member create --address ${member_ip} --subnet-id ${subnet_id} --protocol-port 8000 --wait test_ovn_lb_pool
    echo "Add a floating IP to the load balancer."
    lb_fip=$(openstack floating ip create public1 -f value -c name)
    lb_vip=$(openstack loadbalancer show test_ovn_lb -f value -c vip_address)
    attempt=0
    while [[ $(openstack port list --fixed-ip ip-address=$lb_vip -f value -c ID) == "" ]]; do
        echo "Port for LB with VIP ip addr $lb_vip not available yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "ERROR: Port for LB with VIP ip addr failed to become available"
            openstack port list --fixed-ip ip-address=$lb_vip
            return 1
        fi
        sleep $attempt
    done
    lb_port_id=$(openstack port list --fixed-ip ip-address=$lb_vip -f value -c ID)
    openstack floating ip set $lb_fip --port $lb_port_id

    echo "OVN NB entries for LB:"
    # TODO(mnasiadka): Remove the first part of conditional in G cycle
    if [ $IS_UPGRADE == "yes" ]; then
        sudo ${container_engine} exec ovn_northd ovn-nbctl --db "$ovn_nb_connection" list load_balancer
    else
        sudo ${container_engine} exec ovn_northd ovn-nbctl list load_balancer
    fi

    echo "OVN NB entries for NAT:"
    # TODO(mnasiadka): Remove the first part of conditional in G cycle
    if [ $IS_UPGRADE == "yes" ]; then
        sudo ${container_engine} exec ovn_northd ovn-nbctl --db "$ovn_nb_connection" list nat
    else
        sudo ${container_engine} exec ovn_northd ovn-nbctl list nat
    fi

    echo "Attempt to access the load balanced HTTP server."
    attempts=12
    curl_args=(
        --include
        --location
        --fail
    )
    for i in $(seq 1 ${attempts}); do
        if curl "${curl_args[@]}" $lb_fip:8000; then
            break
        elif [[ $i -eq ${attempts} ]]; then
            echo "Failed to access load balanced service after ${attempts} attempts"
            return 1
        else
            echo "Cannot access load balancer - retrying"
        fi
        sleep 10
    done

    echo "Cleaning up"
    openstack loadbalancer delete test_ovn_lb --cascade --wait
    openstack floating ip delete ${lb_fip}
    openstack server remove floating ip lb_member ${member_fip}
    openstack floating ip delete ${member_fip}
    openstack server delete --wait lb_member
}

function test_ovn_logged {
    test_ovn
    test_octavia
}

function test_ovn_setup {
    echo "Testing OVN and Octavia OVN provider"
    test_ovn_logged &> /tmp/logs/ansible/test-ovn
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing OVN failed. See ansible/test-ovn for details"
    else
        echo "Successfully tested OVN. See ansible/test-ovn for details"
    fi
    return $result
}


container_engine=${1:-docker}
test_ovn_setup
