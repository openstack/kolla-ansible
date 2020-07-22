#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output
export PYTHONUNBUFFERED=1

function check_kibana {
    # Query kibana, and check that the returned page looks like a kibana page.
    KIBANA_URL=${OS_AUTH_URL%:*}:5601
    output_path=$1
    kibana_password=$(awk '$1 == "kibana_password:" { print $2 }' /etc/kolla/passwords.yml)
    args=(
        --include
        --location
        --fail
        --user
        kibana:$kibana_password
    )
    if [[ "$TLS_ENABLED" = "True" ]]; then
        args+=(--cacert $OS_CACERT)
    fi
    if ! curl "${args[@]}" $KIBANA_URL > $output_path; then
        return 1
    fi
    if ! grep '<title>Kibana</title>' $output_path >/dev/null; then
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
    output_path=$1
    args=(
        --include
        --location
        --fail
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

function test_kibana {
    # TODO(mgoddard): Query elasticsearch for logs.
    echo "TESTING: Kibana"
    output_path=$(mktemp)
    attempt=1
    while ! check_kibana $output_path; do
        echo "Kibana not accessible yet"
        attempt=$((attempt+1))
        if [[ $attempt -eq 12 ]]; then
            echo "FAILED: Kibana did not become accessible. Response:"
            cat $output_path
            return 1
        fi
        sleep 10
    done
    echo "SUCCESS: Kibana"
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

function test_prometheus_efk_logged {
    . /etc/kolla/admin-openrc.sh

    test_kibana
    test_grafana
    test_prometheus
}

function test_prometheus_efk {
    echo "Testing prometheus and EFK"
    test_prometheus_efk_logged > /tmp/logs/ansible/test-prometheus-efk 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing prometheus and EFK failed. See ansible/test-prometheus-efk for details"
    else
        echo "Successfully tested prometheus and EFK. See ansible/test-prometheus-efk for details"
    fi
    return $result
}

test_prometheus_efk
