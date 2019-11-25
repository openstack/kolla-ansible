#!/bin/bash

set -o xtrace
set -o errexit
set -o nounset
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function mariadb_stop {
    echo "Stopping the database cluster"
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv stop --yes-i-really-really-mean-it --tags mariadb --skip-tags common
    if [[ $(sudo docker ps -q | grep mariadb | wc -l) -ne 0 ]]; then
        echo "Failed to stop MariaDB cluster"
        return 1
    fi
}

function mariadb_recovery {
    # Recover the database cluster.
    echo "Recovering the database cluster"
    tools/kolla-ansible -i ${RAW_INVENTORY} -vvv mariadb_recovery --tags mariadb --skip-tags common
}

function test_recovery {
    # Stop all nodes in the cluster, then recover.
    mariadb_stop
    mariadb_recovery
}

function test_mariadb_logged {
    RAW_INVENTORY=/etc/kolla/inventory
    test_recovery
}

function test_mariadb {
    echo "Testing MariaDB"
    test_mariadb_logged > /tmp/logs/ansible/test-mariadb 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing MariaDB failed. See ansible/test-mariadb for details"
    else
        echo "Successfully tested MariaDB. See ansible/test-mariadb for details"
    fi
    return $result
}

test_mariadb
