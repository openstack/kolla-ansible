#!/bin/bash

set -o xtrace
set -o errexit

export PYTHONUNBUFFERED=1


function test_swift_logged {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate

    echo "TESTING: Swift"

    CONTAINER_NAME=test_container

    openstack --debug container create $CONTAINER_NAME

    CONTENT='Hello, Swift!'
    FILE_PATH=/tmp/swift_test_object

    echo "$CONTENT" > $FILE_PATH

    openstack --debug object create $CONTAINER_NAME $FILE_PATH

    rm -f $FILE_PATH

    openstack --debug object save $CONTAINER_NAME $FILE_PATH

    SAVED_CONTENT=`cat $FILE_PATH`

    rm -f $FILE_PATH

    if [ "$SAVED_CONTENT" != "$CONTENT" ]; then
        echo 'Content mismatch' >&2
        return 1
    fi

    openstack --debug container show $CONTAINER_NAME

    openstack --debug object store account show

    echo "SUCCESS: Swift"
}

function test_swift {
    echo "Testing Swift"
    log_file=/tmp/logs/ansible/test-swift
    if [[ -f $log_file ]]; then
        log_file=${log_file}-upgrade
    fi
    test_swift_logged > $log_file 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Swift failed. See ansible/test-swift for details"
    else
        echo "Successfully tested Swift. See ansible/test-swift for details"
    fi
    return $result
}


test_swift
