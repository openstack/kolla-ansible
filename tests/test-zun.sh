#!/bin/bash

set -o xtrace
set -o errexit

export PYTHONUNBUFFERED=1

function test_zun_logged {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate

    echo "TESTING: Zun"
    openstack appcontainer service list
    openstack appcontainer host list
    openstack subnet set --no-dhcp demo-subnet
    sudo docker pull alpine
    sudo docker save alpine | openstack image create alpine --public --container-format docker --disk-format raw
    openstack appcontainer run --name test alpine sleep 1000
    attempt=1
    while [[ $(openstack appcontainer show test -f value -c status) != "Running" ]]; do
        echo "Container not running yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Container failed to start"
            openstack appcontainer show test
            return 1
        fi
        sleep 10
    done
    openstack appcontainer list
    openstack appcontainer show test
    openstack appcontainer delete --force --stop test
    echo "SUCCESS: Zun"
}

function test_zun {
    echo "Testing Zun"
    log_file=/tmp/logs/ansible/test-zun
    if [[ -f $log_file ]]; then
        log_file=${log_file}-upgrade
    fi
    test_zun_logged > $log_file 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Zun failed. See ansible/test-zun for details"
    else
        echo "Successfully tested Zun. See ansible/test-zun for details"
    fi
    return $result
}

test_zun
