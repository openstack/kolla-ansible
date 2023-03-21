#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output
export PYTHONUNBUFFERED=1

# TODO(yoctozepto): Avoid duplicating this from prometheus-opensearch
function check_opensearch {
    # Verify that we see a healthy index created due to Fluentd forwarding logs
    local opensearch_url=${OS_AUTH_URL%:*}:9200/_cluster/health
    output_path=$1
    args=(
        --include
        --location
        --fail
    )
    if ! curl "${args[@]}" $opensearch_url > $output_path; then
        return 1
    fi
    # NOTE(mgoddard): Status may be yellow because no indices have been
    # created.
    if ! grep -E '"status":"(green|yellow)"' $output_path >/dev/null; then
        return 1
    fi
}

function check_venus {
    local venus_url=${OS_AUTH_URL%:*}:10010/custom_config
    output_path=$1
    if ! curl --include --fail $venus_url > $output_path; then
        return 1
    fi
    if ! grep -E '"status": "SUPPORTED"' $output_path >/dev/null; then
        return 1
    fi
}

function test_opensearch {
    echo "TESTING: OpenSearch"
    output_path=$(mktemp)
    attempt=1
    while ! check_opensearch $output_path; do
        echo "OpenSearch not accessible yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 12 ]]; then
            echo "FAILED: OpenSearch did not become accessible. Response:"
            cat $output_path
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: OpenSearch"
}

function test_venus {
    echo "TESTING: Venus"
    output_path=$(mktemp)
    attempt=1
    while ! check_venus $output_path; do
        echo "Venus not accessible yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 12 ]]; then
            echo "FAILED: Venus did not become accessible. Response:"
            cat $output_path
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: Venus"
}

function test_venus_scenario_logged {
    . /etc/kolla/admin-openrc.sh

    test_opensearch
    test_venus
}

function test_venus_scenario {
    echo "Testing Venus and OpenSearch"
    test_venus_scenario_logged > /tmp/logs/ansible/test-venus-scenario 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Venus scenario failed. See ansible/test-venus-scenario for details"
    else
        echo "Successfully tested Venus scenario. See ansible/test-venus-scenario for details"
    fi
    return $result
}

test_venus_scenario
