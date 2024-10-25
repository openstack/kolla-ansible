#!/bin/bash
set -o xtrace
set -o pipefail


function test_proxysql_connection_logged {
    mariadb -h $VIP -P$DATABASE_PORT -u$DATABASE_USER -p$DATABASE_PASSWORD -e 'SHOW TABLES'
}

function test_proxysql {
    test_proxysql_connection_logged > /tmp/logs/ansible/test-proxysql 2>&1
    result=$?
    echo $result
    if [[ $result != 0 ]]; then
        echo "Testing ProxySQL failed. See ansible/test-proxysql for details"
    else
        echo "Successfully tested ProxySQL. See ansible/test-proxysql for details"
    fi
    return $result
}
function test_proxysql_ssl_connection {
    query="SELECT SUBSTRING_INDEX(variable_value, ',', -1) AS '' FROM information_schema.session_status WHERE variable_name = 'Ssl_cipher' LIMIT 1;"
    result=$(mariadb -h $VIP -P$DATABASE_PORT -u$DATABASE_USER -p$DATABASE_PASSWORD -e "$query" --silent)
    echo $result
    if [[ "$result" =~ ^[[:space:]]*$ || -z "${result}" ]]; then
        echo "ERROR: SSL is not utilized in ProxySQL"
        return 1
    else
        echo "SSL connection is working properly in proxysql"
        return 0
    fi

}

DATABASE_PORT="${DATABASE_PORT:-3306}"
DATABASE_USER="${DATABASE_USER:-root_shard_0}"
TLS_ENABLED="${TLS_ENABLED:-false}"
if [[ -z "${VIP}"  ]]; then
    echo "VIP  not set"
    exit 1
fi

if [[ -z "${DATABASE_PASSWORD}"  ]]; then
    DATABASE_PASSWORD=$(grep ^database_password /etc/kolla/passwords.yml | cut -d" " -f2)
fi

test_proxysql
if [ "$TLS_ENABLED" = true ]; then
    test_proxysql_ssl_connection
fi



