#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


check_podman_failures() {
    failed_containers=$(sudo podman ps -a --format "{{.Names}}" \
        --filter status=created \
        --filter status=paused \
        --filter status=exited \
        --filter status=unknown)

    for container in $failed_containers; do
        sudo podman inspect $container
        sudo podman logs $container
    done
}


check_podman_unhealthies() {
    unhealthy_containers=$(sudo podman ps -a --format "{{.Names}}" \
        --filter health=unhealthy)
}


check_docker_failures() {
    # All docker container's status are created, restarting, running, removing,
    # paused, exited and dead. Containers without running status are treated as
    # failure. removing is added in docker 1.13, just ignore it now.
    # In addition to that, containers in unhealthy state (from healthchecks)
    # are treated as failure.
    failed_containers=$(sudo docker ps -a --format "{{.Names}}" \
        --filter status=created \
        --filter status=restarting \
        --filter status=paused \
        --filter status=exited \
        --filter status=dead)

    for container in $failed_containers; do
        sudo docker inspect $container
        sudo docker logs $container
    done
}


check_docker_unhealthies() {
    unhealthy_containers=$(sudo docker ps -a --format "{{.Names}}" \
        --filter health=unhealthy)
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
        exit 1;
    fi

    if [[ -n "$failed_containers" ]]; then
        exit 1;
    fi
}

check_failure
