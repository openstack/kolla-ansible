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

    # NOTE(yoctozepto): We have to wait for the container to be deleted due to
    # check-failure.sh checking stopped containers and failing.
    # It is also nice to test that deleting actually works.
    attempt=1
    while openstack appcontainer show test; do
        echo "Container not deleted yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Zun failed to delete the container"
            openstack appcontainer show test
            return 1
        fi
        sleep 10
    done

    echo "SUCCESS: Zun"

    echo "TESTING: Zun Cinder volume attachment"
    openstack volume create --size 2 zun_test_volume
    attempt=1
    while [[ $(openstack volume show zun_test_volume -f value -c status) != "available" ]]; do
        echo "Volume not available yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Volume failed to become available"
            openstack volume show zun_test_volume
            return 1
        fi
        sleep 10
    done
    openstack appcontainer run --name test2 --mount source=zun_test_volume,destination=/data alpine sleep 1000
    attempt=1
    while [[ $(openstack volume show zun_test_volume -f value -c status) != "in-use" ]]; do
        echo "Volume not attached yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Volume failed to attach"
            openstack volume show zun_test_volume
            return 1
        fi
        sleep 10
    done
    attempt=1
    while [[ $(openstack appcontainer show test2 -f value -c status) != "Running" ]]; do
        echo "Container not running yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Container failed to start"
            openstack appcontainer show test2
            return 1
        fi
        sleep 10
    done
    openstack appcontainer delete --stop test2
    attempt=1
    while [[ $(openstack volume show zun_test_volume -f value -c status) != "available" ]]; do
        echo "Volume not detached yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Volume failed to detach"
            openstack volume show zun_test_volume
            return 1
        fi
        sleep 10
    done
    openstack volume delete zun_test_volume
    echo "SUCCESS: Zun Cinder volume attachment"

    echo "TESTING: Zun capsule"
    cat >/tmp/capsule.yaml <<EOF
capsuleVersion: beta
kind: capsule
metadata:
  name: capsule-test
spec:
  containers:
  - image: alpine
    command:
    - sleep
    - "1000"
EOF
    zun capsule-create -f /tmp/capsule.yaml
    attempt=1
    while [[ $(zun capsule-describe capsule-test | awk '/ status /{print $4}') != "Running" ]]; do
        echo "Capsule not running yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Capsule failed to start"
            zun capsule-describe capsule-test
            return 1
        fi
        sleep 10
    done
    zun capsule-list
    zun capsule-describe capsule-test
    zun capsule-delete capsule-test

    attempt=1
    while zun capsule-describe capsule-test; do
        echo "Capsule not deleted yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "Zun failed to delete the capsule"
            zun capsule-describe capsule-test
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: Zun capsule"
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
