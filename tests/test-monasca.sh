#!/bin/bash

set -o xtrace
set -o errexit
set -o nounset
set -o pipefail

function test_monasca_metrics {
    # Check that the monitoring endpoints are registered
    openstack endpoint list -f value --service monitoring --interface internal -c URL
    openstack endpoint list -f value --service monitoring --interface public -c URL

    # Run some CLI commands
    MONASCA_PROJECT_ID=$(openstack project list --user monasca-agent -f value -c ID)
    monasca metric-list --tenant-id "$MONASCA_PROJECT_ID"
    monasca alarm-list
    monasca notification-list

    # Test the metric pipeline by waiting for some metrics to arrive from the
    # Monasca Agent. If the metric doesn't yet exist, nothing is returned.
    METRIC_STATS_CMD="monasca metric-statistics mem.free_mb --tenant-id $MONASCA_PROJECT_ID COUNT -300 --merge_metrics"
    for i in {1..60}; do
        if [[ $($METRIC_STATS_CMD) == *'mem.free_mb'* ]]; then
            return 0
        fi
        sleep 1
    done
    return 1
}

function test_monasca_logs {
    # Check that the logging endpoints are registered
    openstack endpoint list -f value --service logging --interface internal -c URL
    openstack endpoint list -f value --service logging --interface public -c URL

    # Test the logging pipeline by waiting for some logs to arrive from
    # Fluentd into the Monasca Elasticsearch index
    # TODO: Use index name set in config

    # NOTE(dszumski): When querying logs via the Monasca Log API *is*
    # supported, we can replace this in favour of calling querying the Log API.
    ELASTICSEARCH_URL=${OS_AUTH_URL%:*}:9200
    for i in {1..60}; do
        if [[ $(curl -s -X GET $ELASTICSEARCH_URL/_cat/indices?v) == *"monasca-"* ]]; then
            return 0
        fi
        sleep 1
    done
    return 1
}

function test_monasca_logged {
    . /etc/kolla/admin-openrc.sh
    # Activate virtualenv to access Monasca client
    . ~/openstackclient-venv/bin/activate

    test_monasca_metrics
    result=$?
    if [[ $result != 0 ]]; then
        echo "Failed testing metrics pipeline"
        return $result
    fi

    test_monasca_logs
    result=$?
    if [[ $result != 0 ]]; then
        echo "Failed testing logging pipeline"
        return $result
    fi
}

function test_monasca {
    echo "Testing Monasca"
    test_monasca_logged > /tmp/logs/ansible/test-monasca 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Monasca test failed. See ansible/test-monasca for details"
    else
        echo "Successfully tested Monasca. See ansible/test-monasca for details"
    fi
    return $result
}

test_monasca
