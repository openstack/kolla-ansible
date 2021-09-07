#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


check_failure() {
    # All docker container's status are created, restarting, running, removing,
    # paused, exited and dead. Containers without running status are treated as
    # failure. removing is added in docker 1.13, just ignore it now.
    # In addition to that, containers in unhealthy state (from healthchecks)
    # are trated as failure.
    failed_containers=$(sudo docker ps -a --format "{{.Names}}" \
        --filter status=created \
        --filter status=restarting \
        --filter status=paused \
        --filter status=exited \
        --filter status=dead)

    unhealthy_containers=$(sudo docker ps -a --format "{{.Names}}" \
        --filter health=unhealthy)

    if [[ -n "$unhealthy_containers" ]]; then
        exit 1;
    fi

    # NOTE(mgoddard): monasca-thresh is a one-shot container that exits but
    # remains in place, leaving it with a status of exited. This is harmless.
    if [[ "$failed_containers" = "monasca_thresh" ]]; then
        exit 0
    fi

    if [[ -n "$failed_containers" ]]; then
        exit 1;
    fi
}

check_failure
