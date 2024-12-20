#!/bin/bash

set -o xtrace
set -o pipefail

# Enable unbuffered output
export PYTHONUNBUFFERED=1

function check_skyline_sso_enabled {
    skyline_endpoint=$(openstack endpoint list --interface public --service skyline -f value -c URL)
    # 9998 is the default port for skyline apiserver.
    # 9999 is the default port for skyline console.
    skyline_sso_url="${skyline_endpoint//9998/9999}/api/openstack/skyline/api/v1/sso"

    output_path=$1
    if ! curl -k --include --fail $skyline_sso_url -H "Accept: application/json" -H "Content-Type: application/json"  > $output_path; then
        return 1
    fi
    if ! grep -E '"enable_sso":true' $output_path >/dev/null; then
        return 1
    fi
}

function test_skyline_sso {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate
    test_skyline_sso_enabled
}

function test_skyline_sso_enabled {
    echo "TESTING: Skyline SSO enabled"
    output_path=$(mktemp)
    attempt=1
    while ! check_skyline_sso_enabled $output_path; do
        echo "Skyline not accessible yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 12 ]]; then
            echo "FAILED: Skyline did not become accessible or SSO not enabled. Response:"
            cat $output_path
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: Skyline SSO enabled"
}

function test_skyline_sso_scenario {
    echo "Testing Skyline SSO"
    test_skyline_sso > /tmp/logs/ansible/test-skyline-sso 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Skyline SSO failed. See ansible/test-skyline-sso for details"
    else
        echo "Successfully tested Skyline SSO. See ansible/test-skyline-sso for details"
    fi
    return $result
}

test_skyline_sso_scenario
