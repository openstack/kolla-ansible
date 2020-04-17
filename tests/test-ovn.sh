#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output
export PYTHONUNBUFFERED=1

function test_ovn_logged {
    # NOTE(yoctozepto): could use real ini parsing but this is fine for now
    local neutron_ml2_conf_path=/etc/kolla/neutron-server/ml2_conf.ini
    ovn_nb_connection=$(sudo grep -P -o -e "(?<=^ovn_nb_connection = ).*" "$neutron_ml2_conf_path")
    ovn_sb_connection=$(sudo grep -P -o -e "(?<=^ovn_sb_connection = ).*" "$neutron_ml2_conf_path")

    # List OVN NB/SB entries
    echo "OVN NB DB entries:"
    sudo docker exec ovn_northd ovn-nbctl --db "$ovn_nb_connection" show

    echo "OVN SB DB entries:"
    sudo docker exec ovn_northd ovn-sbctl --db "$ovn_sb_connection" show

    # Test OVSDB cluster state
    if [[ $BASE_DISTRO =~ ^(debian|ubuntu)$ ]]; then
        OVNNB_STATUS=$(sudo docker exec ovn_nb_db ovs-appctl -t /var/run/openvswitch/ovnnb_db.ctl cluster/status OVN_Northbound)
        OVNSB_STATUS=$(sudo docker exec ovn_sb_db ovs-appctl -t /var/run/openvswitch/ovnsb_db.ctl cluster/status OVN_Southbound)
    else
        OVNNB_STATUS=$(sudo docker exec ovn_nb_db ovs-appctl -t /var/run/ovn/ovnnb_db.ctl cluster/status OVN_Northbound)
        OVNSB_STATUS=$(sudo docker exec ovn_sb_db ovs-appctl -t /var/run/ovn/ovnsb_db.ctl cluster/status OVN_Southbound)
    fi

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
}

function test_ovn {
    echo "Testing OVN"
    test_ovn_logged > /tmp/logs/ansible/test-ovn 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing OVN failed. See ansible/test-ovn for details"
    else
        echo "Successfully tested OVN. See ansible/test-ovn for details"
    fi
    return $result
}

test_ovn
