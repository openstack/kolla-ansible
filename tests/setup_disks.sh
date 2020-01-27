#!/bin/bash

# $1: scenario / ceph store type

set -o xtrace
set -o errexit

mkdir -p /opt/data/kolla

if [ $1 = 'zun' ]; then
    # create cinder-volumes volume group for cinder lvm backend
    free_device=$(losetup -f)
    fallocate -l 5G /var/lib/cinder_data.img
    losetup $free_device /var/lib/cinder_data.img
    pvcreate $free_device
    vgcreate cinder-volumes $free_device
elif [ $1 = 'swift' ]; then
    # swift partition
    free_device=$(losetup -f)
    fallocate -l 5G /var/lib/swift_data.img
    losetup $free_device /var/lib/swift_data.img
    parted $free_device -s -- mklabel gpt mkpart KOLLA_SWIFT_DATA 1 -1
    free_partition=${free_device}p1
    mkfs.xfs -L d0 $free_partition
elif [ $1 = 'ceph-lvm' ]; then
    free_device=$(losetup -f)
    fallocate -l 10G /var/lib/ceph-osd1.img
    losetup $free_device /var/lib/ceph-osd1.img
    pvcreate $free_device
    vgcreate cephvg $free_device
    lvcreate -l 100%FREE -n cephlv cephvg
else
    echo "Unknown type" >&2
    exit 1
fi

partprobe
