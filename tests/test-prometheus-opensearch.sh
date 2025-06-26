#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output
export PYTHONUNBUFFERED=1

function check_opensearch_dashboards {
    # Perform and validate a basic status page check
    OPENSEARCH_DASHBOARDS_URL=${OS_AUTH_URL%:*}:5601/api/status
    output_path=$1
    opensearch_dashboards_password=$(awk '$1 == "opensearch_dashboards_password:" { print $2 }' /etc/kolla/passwords.yml)
    args=(
        --include
        --location
        --fail
        --user
        opensearch:$opensearch_dashboards_password
    )
    if [[ "$TLS_ENABLED" = "True" ]]; then
        args+=(--cacert $OS_CACERT)
    fi
    if ! curl "${args[@]}" $OPENSEARCH_DASHBOARDS_URL > $output_path; then
        return 1
    fi
    if ! grep 'Looking good' $output_path >/dev/null; then
        return 1
    fi
}

function check_opensearch {
    # Verify that we see a healthy index created due to Fluentd forwarding logs
    OPENSEARCH_URL=${OS_AUTH_URL%:*}:9200/_cluster/health
    output_path=$1
    args=(
        --include
        --location
        --fail
    )
    if [[ "$TLS_ENABLED" = "True" ]]; then
        args+=(--cacert $OS_CACERT)
    fi
    if ! curl "${args[@]}" $OPENSEARCH_URL > $output_path; then
        return 1
    fi
    # NOTE(mgoddard): Status may be yellow because no indices have been
    # created.
    if ! grep -E '"status":"(green|yellow)"' $output_path >/dev/null; then
        return 1
    fi
}

function check_grafana {
    # Query grafana, and check that the returned page looks like a grafana page.
    GRAFANA_URL=${OS_AUTH_URL%:*}:3000
    output_path=$1
    grafana_password=$(awk '$1 == "grafana_admin_password:" { print $2 }' /etc/kolla/passwords.yml)
    args=(
        --include
        --location
        --fail
        --user
        admin:$grafana_password
    )
    if [[ "$TLS_ENABLED" = "True" ]]; then
        args+=(--cacert $OS_CACERT)
    fi
    if ! curl "${args[@]}" $GRAFANA_URL > $output_path; then
        return 1
    fi
    if ! grep '<title>Grafana</title>' $output_path >/dev/null; then
        return 1
    fi
}

function check_prometheus {
    # Query prometheus graph, and check that the returned page looks like a
    # prometheus page.
    PROMETHEUS_URL=${OS_AUTH_URL%:*}:9091/graph
    prometheus_password=$(awk '$1 == "prometheus_password:" { print $2 }' /etc/kolla/passwords.yml)
    output_path=$1
    args=(
        --include
        --location
        --fail
        --user
        admin:$prometheus_password
    )
    if [[ "$TLS_ENABLED" = "True" ]]; then
        args+=(--cacert $OS_CACERT)
    fi
    if ! curl "${args[@]}" $PROMETHEUS_URL > $output_path; then
        return 1
    fi
    if ! grep '<title>Prometheus' $output_path >/dev/null; then
        return 1
    fi
}

function test_opensearch_dashboards {
    echo "TESTING: OpenSearch Dashboards"
    output_path=$(mktemp)
    attempt=1
    while ! check_opensearch_dashboards $output_path; do
        echo "OpenSearch Dashboards not accessible yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 12 ]]; then
            echo "FAILED: OpenSearch Dashboards did not become accessible. Response:"
            cat $output_path
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: OpenSearch Dashboards"
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

function test_grafana {
    echo "TESTING: Grafana"
    output_path=$(mktemp)
    attempt=1
    while ! check_grafana $output_path; do
        echo "Grafana not accessible yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 12 ]]; then
            echo "FAILED: Grafana did not become accessible. Response:"
            cat $output_path
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: Grafana"
}

function test_prometheus {
    # TODO(mgoddard): Query metrics.
    echo "TESTING: Prometheus"
    output_path=$(mktemp)
    attempt=1
    while ! check_prometheus $output_path; do
        echo "Prometheus not accessible yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 12 ]]; then
            echo "FAILED: Prometheus did not become accessible. Response:"
            cat $output_path
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: Prometheus"
}

function test_prometheus_opensearch_logged {
    . /etc/kolla/admin-openrc.sh
    test_opensearch_dashboards
    test_opensearch
    test_grafana
    test_prometheus
}

function test_prometheus_opensearch {
    echo "Testing prometheus and OpenSearch"
    test_prometheus_opensearch_logged > /tmp/logs/ansible/test-prometheus-opensearch 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing prometheus and OpenSearch failed. See ansible/test-prometheus-opensearch for details"
    else
        echo "Successfully tested prometheus and OpenSearch. See ansible/test-prometheus-opensearch for details"
    fi
    return $result
}

test_prometheus_opensearch
