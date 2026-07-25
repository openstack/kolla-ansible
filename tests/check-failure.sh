#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

# neutron_agents_wrappers (see ansible/roles/neutron) spawns per-namespace
# helper containers (dnsmasq/haproxy/keepalived) that are not managed by
# Kolla and can be created/removed by Neutron independently of the deploy,
# e.g. neutron_dhcp_agent_dnsmasq_qdhcp-<uuid>. Ignore them in these checks.
IGNORE_CONTAINERS_REGEX='_(qdhcp|qrouter|ovnmeta)-'

filter_unmanaged_containers() {
    grep -Ev "$IGNORE_CONTAINERS_REGEX" || true
}


check_podman_failures() {
    failed_containers=$(sudo podman ps -a --format "{{.Names}}" \
        --filter status=created \
        --filter status=exited \
        --filter status=paused \
        --filter status=removing \
        --filter status=unknown \
        | filter_unmanaged_containers)

    for container in $failed_containers; do
        sudo podman inspect $container
        sudo podman logs $container
    done
}


check_podman_unhealthies() {
    while [ -n "$(sudo podman ps -a --format "{{.Names}}" --filter health=starting)" ]; do
        echo "Containers with health status 'starting', waiting..."
        sleep 10
    done

    unhealthy_containers=$(sudo podman ps -a --format "{{.Names}}" \
        --filter health=unhealthy \
        | filter_unmanaged_containers)

    for container in $unhealthy_containers; do
        echo "Discovered unhealthy container: $container"
        echo "$container - podman inspect"
        sudo podman inspect $container
        echo "$container - ps axwuf"
        sudo podman exec $container ps axwuf
        echo "$container - ss -anp"
        sudo podman exec $container ss -anp
    done
}


check_docker_failures() {
    # All docker container's status are created, restarting, running, removing,
    # paused, exited and dead. Containers without running status are treated as
    # failure. removing is added in docker 1.13, just ignore it now.
    # In addition to that, containers in unhealthy state (from healthchecks)
    # are treated as failure.
    failed_containers=$(sudo docker ps -a --format "{{.Names}}" \
        --filter status=created \
        --filter status=exited \
        --filter status=dead \
        --filter status=paused \
        --filter status=removing \
        --filter status=restarting \
        | filter_unmanaged_containers)

    for container in $failed_containers; do
        sudo docker inspect $container
        sudo docker logs $container
    done
}


check_docker_unhealthies() {
    while [ -n "$(sudo docker ps -a --format "{{.Names}}" --filter health=starting)" ]; do
        echo "Containers with health status 'starting', waiting..."
        sleep 10
    done

    unhealthy_containers=$(sudo docker ps -a --format "{{.Names}}" \
        --filter health=unhealthy \
        | filter_unmanaged_containers)

    for container in $unhealthy_containers; do
        echo "Discovered unhealthy container: $container"
        echo "$container - docker inspect"
        sudo docker inspect $container
        echo "$container - ps axwuf"
        sudo docker exec $container ps axwuf
        echo "$container - ss -anp"
        sudo docker exec $container ss -anp
    done
}


check_failure() {
    if [ "$CONTAINER_ENGINE" = "docker" ]; then
        check_docker_failures
        check_docker_unhealthies
    elif [ "$CONTAINER_ENGINE" = "podman" ]; then
        check_podman_failures
        check_podman_unhealthies
    else
        echo "Invalid container engine: ${CONTAINER_ENGINE}"
        exit 1
    fi

    if [[ -n "$unhealthy_containers" ]]; then
        # NOTE(mnasiadka): try checking them again, because usually they are healthy now
        echo "Discovered unhealthy containers - sleeping 60 seconds and retrying check"
        sleep 60
        if [ "$CONTAINER_ENGINE" = "docker" ]; then
            check_docker_unhealthies
        elif [ "$CONTAINER_ENGINE" = "podman" ]; then
            check_podman_unhealthies
        fi
        # NOTE(mnasiadka): If they're unhealthy again - let's fail
        if [[ -n "$unhealthy_containers" ]]; then
            exit 1;
        fi
    fi

    if [[ -n "$failed_containers" ]]; then
        exit 1;
    fi
}

check_failure
