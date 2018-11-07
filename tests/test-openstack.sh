#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function test_openstack {
    # Wait for service ready
    sleep 15
    . /etc/kolla/admin-openrc.sh
    # TODO(Jeffrey4l): Restart the memcached container to cleanup all cache.
    # Remove this after this bug is fixed
    # https://bugs.launchpad.net/oslo.cache/+bug/1590779
    sudo docker restart memcached
    nova --debug service-list
    openstack --debug network agent list
    tools/init-runonce
    nova --debug boot --poll --image $(openstack image list | awk '/cirros/ {print $2}') --nic net-id=$(openstack network list | awk '/demo-net/ {print $2}') --flavor 1 kolla_boot_test

    nova --debug list
    # If the status is not ACTIVE, print info and exit 1
    nova --debug show kolla_boot_test | awk '{buf=buf"\n"$0} $2=="status" && $4!="ACTIVE" {failed="yes"}; END {if (failed=="yes") {print buf; exit 1}}'
    if echo $ACTION | grep -q "ceph"; then
        openstack volume create --size 2 test_volume
        openstack server add volume kolla_boot_test test_volume --device /dev/vdb
    fi
    if echo $ACTION | grep -q "zun"; then
        openstack --debug appcontainer service list
        openstack --debug appcontainer host list
        # TODO(hongbin): Run a Zun container and assert the container becomes
        # Running
    fi
}

test_openstack
