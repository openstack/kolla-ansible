#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

export PYTHONUNBUFFERED=1


function init_runonce {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate

    echo "Initialising OpenStack resources via init-runonce"
    KOLLA_DEBUG=1 tools/init-runonce |& gawk '{ print strftime("%F %T"), $0; }' &> /tmp/logs/ansible/init-runonce

    echo "Setting address on the external network bridge"
    if [[ $SCENARIO == "linuxbridge" ]]; then
        # NOTE(yoctozepto): linuxbridge agent manages its bridges by itself
        # hence, we need to find the current name of the external network bridge
        devname=$(basename $(readlink /sys/class/net/${EXT_NET_SLAVE_DEVICE}/master))
    else
        devname=br-ex
        # NOTE(yoctozepto): ovs virtual interfaces are down (not used) by default
        # hence, we need to bring the external network bridge up
        sudo ip link set ${devname} up
    fi
    sudo ip addr add ${EXT_NET_LOCAL_ADDR} dev ${devname}
}


init_runonce
