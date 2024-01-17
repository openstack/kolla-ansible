#!/bin/bash

set -o xtrace
set -o pipefail

# Enable unbuffered output
export PYTHONUNBUFFERED=1

function check_skyline {
    skyline_endpoint=$(openstack endpoint list --interface public --service skyline -f value -c URL)
    # 9998 is the default port for skyline apiserver.
    # 9999 is the default port for skyline console.
    skyline_login_url="${skyline_endpoint//9998/9999}/api/openstack/skyline/api/v1/login"
    skyline_body="{\"region\": \"${OS_REGION_NAME}\", \"domain\": \"${OS_USER_DOMAIN_NAME}\", \"username\": \"${OS_USERNAME}\", \"password\": \"${OS_PASSWORD}\"}"

    output_path=$1
    if ! curl -k --include --fail -X POST $skyline_login_url -H "Accept: application/json" -H "Content-Type: application/json" -d "${skyline_body}"  > $output_path; then
        return 1
    fi
    if ! grep -E '"keystone_token":' $output_path >/dev/null; then
        return 1
    fi
}

function check_skyline_sso_disabled {
    skyline_endpoint=$(openstack endpoint list --interface public --service skyline -f value -c URL)
    # 9998 is the default port for skyline apiserver.
    # 9999 is the default port for skyline console.
    skyline_sso_url="${skyline_endpoint//9998/9999}/api/openstack/skyline/api/v1/sso"

    output_path=$1
    if ! curl -k --include --fail $skyline_sso_url -H "Accept: application/json" -H "Content-Type: application/json"  > $output_path; then
        return 1
    fi
    if ! grep -E '"enable_sso":false' $output_path >/dev/null; then
        return 1
    fi
}

function test_skyline {
    echo "TESTING: Skyline"
    output_path=$(mktemp)
    attempt=1
    while ! check_skyline $output_path; do
        echo "Skyline not accessible yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 12 ]]; then
            echo "FAILED: Skyline did not become accessible. Response:"
            cat $output_path
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: Skyline"
}

function test_skyline_logged {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate
    test_skyline
}

function test_skyline_sso_disabled {
    echo "TESTING: Skyline SSO disabled"
    output_path=$(mktemp)
    attempt=1
    while ! check_skyline_sso_disabled $output_path; do
        echo "Skyline not accessible yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 12 ]]; then
            echo "FAILED: Skyline did not become accessible or SSO enabled. Response:"
            cat $output_path
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: Skyline SSO disabled"
}

function test_skyline_scenario {
    echo "Testing Skyline"
    test_skyline_logged > /tmp/logs/ansible/test-skyline 2>&1 && test_skyline_sso_disabled >> /tmp/logs/ansible/test-skyline 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Skyline failed. See ansible/test-skyline for details"
    else
        echo "Successfully tested Skyline. See ansible/test-skyline for details"
    fi
    return $result
}

test_skyline_scenario
