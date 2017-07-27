#!/bin/bash

copy_logs() {
    set +o errexit
    LOG_DIR=$(readlink -f /tmp/logs)

    cp -rnL /var/lib/docker/volumes/kolla_logs/_data/* ${LOG_DIR}/kolla/
    cp -rnL /etc/kolla/* ${LOG_DIR}/kolla_configs/
    cp -rvnL /var/log/* ${LOG_DIR}/system_logs/


    if [[ -x "$(command -v journalctl)" ]]; then
        journalctl --no-pager > ${LOG_DIR}/system_logs/syslog.txt
        journalctl --no-pager -u docker.service > ${LOG_DIR}/system_logs/docker.log
    else
        cp /var/log/upstart/docker.log ${LOG_DIR}/system_logs/docker.log
    fi

    sudo cp -r /etc/sudoers.d ${LOG_DIR}/system_logs/
    sudo cp /etc/sudoers ${LOG_DIR}/system_logs/sudoers.txt

    df -h > ${LOG_DIR}/system_logs/df.txt
    free  > ${LOG_DIR}/system_logs/free.txt
    sudo parted -l > ${LOG_DIR}/system_logs/parted-l.txt
    mount > ${LOG_DIR}/system_logs/mount.txt
    env > ${LOG_DIR}/system_logs/env.txt

    if [ `command -v dpkg` ]; then
        dpkg -l > ${LOG_DIR}/system_logs/dpkg-l.txt
    fi
    if [ `command -v rpm` ]; then
        rpm -qa > ${LOG_DIR}/system_logs/rpm-qa.txt
    fi

    # final memory usage and process list
    ps -eo user,pid,ppid,lwp,%cpu,%mem,size,rss,cmd > ${LOG_DIR}/system_logs/ps.txt

    # docker related information
    (docker info && docker images && docker ps -a) > ${LOG_DIR}/system_logs/docker-info.txt

    # Rename files to .txt; this is so that when displayed via
    # logs.openstack.org clicking results in the browser shows the
    # files, rather than trying to send it to another app or make you
    # download it, etc.

    # Rename all .log files to .txt files
    for f in $(find ${LOG_DIR}/{system_logs,kolla,docker_logs} -name "*.log"); do
        sudo mv $f ${f/.log/.txt}
    done

    sudo find ${LOG_DIR}/{system_logs,kolla,docker_logs} -iname '*.txt' -execdir gzip -f -9 {} \+
    sudo find ${LOG_DIR}/{system_logs,kolla,docker_logs} -iname '*.json' -execdir gzip -f -9 {} \+

    set +o errexit
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
