#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output
export PYTHONUNBUFFERED=1

function test_aodh {
    echo "TESTING: Aodh"
    openstack alarm list
    echo "SUCCESS: Aodh"
}

function test_gnocchi {
    echo "TESTING: Gnocchi"
    openstack metric list
    openstack metric resource list
    echo "SUCCESS: Gnocchi"
}

function test_telemetry_scenario_logged {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate
    test_aodh
    test_gnocchi
}

function test_telemetry_scenario {
    echo "Testing Telemetry"
    test_telemetry_scenario_logged > /tmp/logs/ansible/test-telemetry-scenario 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Telemetry scenario failed. See ansible/test-telemetry-scenario for details"
    else
        echo "Successfully tested Telemetry scenario. See ansible/test-telemetry-scenario for details"
    fi
    return $result
}

test_telemetry_scenario
