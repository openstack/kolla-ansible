#!/bin/bash

set -o xtrace
set -o errexit

export PYTHONUNBUFFERED=1


function check_dashboard {
    # Query the dashboard, and check that the returned page looks like a login
    # page.
    DASHBOARD_URL=${OS_AUTH_URL%:*}
    output_path=$1
    args=(
        --include
        --location
        --fail
    )
    if [[ "$TLS_ENABLED" = "True" ]]; then
        args+=(--cacert $OS_CACERT)
    fi
    if ! curl "${args[@]}" $DASHBOARD_URL > $output_path; then
        return 1
    fi
    if ! grep Login $output_path >/dev/null; then
        return 1
    fi
}

function test_dashboard_logged {
    . /etc/kolla/admin-openrc.sh

    echo "TESTING: Dashboard"
    # The dashboard has been known to take some time to become accessible, so
    # use retries.
    output_path=$(mktemp)
    attempt=1
    while ! check_dashboard $output_path; do
        echo "Dashboard not accessible yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 30 ]]; then
            echo "FAILED: Dashboard did not become accessible. Response:"
            cat $output_path
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: Dashboard"
}

function test_dashboard {
    echo "Testing dashboard"
    log_file=/tmp/logs/ansible/test-dashboard
    if [[ -f $log_file ]]; then
        log_file=${log_file}-upgrade
    fi
    test_dashboard_logged > $log_file 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing dashboard failed. See ansible/test-dashboard for details"
    else
        echo "Successfully tested dashboard. See ansible/test-dashboard for details"
    fi
    return $result
}


test_dashboard
