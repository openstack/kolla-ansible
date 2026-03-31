#!/bin/bash
set -o xtrace
set -o pipefail

function test_proxysql_upgrade {
    echo "Testing upgrading ProxySQL"
    test_proxysql_upgrade_logged > /tmp/logs/ansible/test-proxysql-upgrade 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing ProxySQL failed. See ansible/test-proxysql-upgrade for details"
    else
        echo "Successfully tested ProxySQL. See ansible/test-proxysql-upgrade for details"
    fi
    return $result
}

function test_proxysql_upgrade_logged {
    RAW_INVENTORY=/etc/kolla/inventory
    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate
    kolla-ansible deploy -i ${RAW_INVENTORY} -t loadbalancer -e proxysql_version=3 || return $?
    version=$(sudo $container_engine exec proxysql proxysql --version)
    echo "ProxySQL version: $version"
    echo $version | grep -q "3.0"
    return $?
}

container_engine="${1:-${CONTAINER_ENGINE:-docker}}"
test_proxysql_upgrade
