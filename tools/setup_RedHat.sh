#!/bin/bash

set -o xtrace
set -o errexit

function setup_disk {
    if [ ! -f /swapfile ]; then
        sudo swapoff -a
        sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
        sudo chmod 0600 /swapfile
        sudo mkswap /swapfile
        sudo /sbin/swapon /swapfile
    fi

    if [ ! -f /docker ]; then
        sudo dd if=/dev/zero of=/docker bs=1M count=20480
        sudo losetup -f /docker
        DEV=$(losetup -a | awk -F: '/\/docker/ {print $1}')
    fi

# Excerpts from https://github.com/openstack-infra/devstack-gate/blob/dc49f9e6eb18e42c6b175e4e146fa8f3b7633279/functions.sh#L306
    if [ -b /dev/xvde ]; then
        DEV2='/dev/xvde'
        if mount | grep ${DEV2} > /dev/null; then
            echo "*** ${DEV2} appears to already be mounted"
            echo "*** ${DEV2} unmounting and reformating"
            sudo umount ${DEV2}
        fi
        sudo parted ${DEV2} --script -- mklabel msdos
        sync
        sudo partprobe
        sudo mkfs.ext4 ${DEV2}
        sudo mount ${DEV2} /mnt
        sudo find /opt/ -mindepth 1 -maxdepth 1 -exec mv {} /mnt/ \;
        sudo umount /mnt
        sudo mount ${DEV2} /opt
        grep -q ${DEV2} /proc/mounts || exit 1
    fi

    # Format Disks and setup Docker to use BTRFS
    sudo parted ${DEV} -s -- mklabel msdos
    sudo rm -rf /var/lib/docker
    sudo mkdir /var/lib/docker

    # We want to snapshot the entire docker directory so we have to first create a
    # subvolume and use that as the root for the docker directory.
    sudo mkfs.btrfs -f ${DEV}
    sudo mount ${DEV} /var/lib/docker
    sudo btrfs subvolume create /var/lib/docker/docker
    sudo umount /var/lib/docker
    sudo mount -o noatime,subvol=docker ${DEV} /var/lib/docker
}

# (SamYaple)TODO: Remove the path overriding
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

sudo tee /etc/yum.repos.d/docker.repo << EOF
[docker]
name=Docker Main Repository
baseurl=https://yum.dockerproject.org/repo/main/centos/7
enabled=1
gpgcheck=1
gpgkey=https://yum.dockerproject.org/gpg
EOF

sudo yum -y install libffi-devel openssl-devel docker-engine docker-engine-selinux btrfs-progs

setup_disk

# Setup Docker
sudo mkdir /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/kolla.conf << EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd --storage-driver btrfs --insecure-registry $(cat /etc/nodepool/primary_node_private):4000
MountFlags=shared
EOF

sudo systemctl daemon-reload

sudo systemctl start docker
sudo docker info

echo "Completed $0."
