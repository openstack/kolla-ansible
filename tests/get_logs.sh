#!/bin/bash

set +o errexit

copy_logs() {
    LOG_DIR=/tmp/logs

    cp -rnL /var/lib/docker/volumes/kolla_logs/_data/* ${LOG_DIR}/kolla/
    cp -rnL /etc/kolla/* ${LOG_DIR}/kolla_configs/
    cp -rvnL /var/log/* ${LOG_DIR}/system_logs/


    if [[ -x "$(command -v journalctl)" ]]; then
        journalctl --no-pager > ${LOG_DIR}/system_logs/syslog.txt
        journalctl --no-pager -u docker.service > ${LOG_DIR}/system_logs/docker.log
    else
        cp /var/log/upstart/docker.log ${LOG_DIR}/system_logs/docker.log
    fi

    cp -r /etc/sudoers.d ${LOG_DIR}/system_logs/
    cp /etc/sudoers ${LOG_DIR}/system_logs/sudoers.txt

    df -h > ${LOG_DIR}/system_logs/df.txt
    free  > ${LOG_DIR}/system_logs/free.txt
    parted -l > ${LOG_DIR}/system_logs/parted-l.txt
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

    # ceph related logs
    if [[ $(docker ps --filter name=ceph_mon --format "{{.Names}}") ]]; then
        docker exec ceph_mon ceph --connect-timeout 5 -s > ${LOG_DIR}/kolla/ceph/ceph_s.txt
        # NOTE(yoctozepto): osd df removed on purpose to avoid CI POST_FAILURE due to a possible hang:
        # as of ceph mimic it hangs when MON is operational but MGR not
        # its usefulness is mediocre and having POST_FAILUREs is bad
        docker exec ceph_mon ceph --connect-timeout 5 osd tree > ${LOG_DIR}/kolla/ceph/ceph_osd_tree.txt
    fi

    # bifrost related logs
    if [[ $(docker ps --filter name=bifrost_deploy --format "{{.Names}}") ]]; then
        for service in dnsmasq ironic-api ironic-conductor ironic-inspector mariadb nginx rabbitmq-server; do
            mkdir -p ${LOG_DIR}/kolla/$service
            docker exec bifrost_deploy systemctl status $service > ${LOG_DIR}/kolla/$service/systemd-status-$service.txt
        done
        docker exec bifrost_deploy journalctl -u mariadb > ${LOG_DIR}/kolla/mariadb/mariadb.txt
        docker exec bifrost_deploy journalctl -u rabbitmq-server > ${LOG_DIR}/kolla/rabbitmq-server/rabbitmq.txt
    fi

    for container in $(docker ps -a --format "{{.Names}}"); do
        docker logs --tail all ${container} > ${LOG_DIR}/docker_logs/${container}.txt
    done

    # Rename files to .txt; this is so that when displayed via
    # logs.openstack.org clicking results in the browser shows the
    # files, rather than trying to send it to another app or make you
    # download it, etc.

    # Rename all .log files to .txt files
    for f in $(find ${LOG_DIR}/{system_logs,kolla,docker_logs} -name "*.log"); do
        mv $f ${f/.log/.txt}
    done

    chmod -R 777 ${LOG_DIR}
}

copy_logs
