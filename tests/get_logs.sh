#!/bin/bash

copy_logs() {
    cp -rnL /var/lib/docker/volumes/kolla_logs/_data/* /tmp/logs/kolla/
    cp -rnL /etc/kolla/* /tmp/logs/kolla_configs/
    cp -rvnL /var/log/* /tmp/logs/system_logs/


    if [[ -x "$(command -v journalctl)" ]]; then
        journalctl --no-pager -u docker.service > /tmp/logs/system_logs/docker.log
    else
        cp /var/log/upstart/docker.log /tmp/logs/system_logs/docker.log
    fi
}

check_failure() {
    # Command failures after this point can be expected
    set +o errexit

    docker images
    docker ps -a
    # All docker container's status are created, restarting, running, removing,
    # paused, exited and dead. Containers without running status are treated as
    # failure. removing is added in docker 1.13, just ignore it now.
    failed_containers=$(docker ps -a --format "{{.Names}}" \
        --filter status=created \
        --filter status=restarting \
        --filter status=paused \
        --filter status=exited \
        --filter status=dead)

    for failed in ${failed_containers}; do
        docker logs --tail all ${failed} > /tmp/logs/docker_logs/${failed}
    done

    copy_logs

    if [[ -n "$failed_containers" ]]; then
        exit 1;
    fi
}

check_failure
