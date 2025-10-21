#!/bin/bash

set +o errexit

copy_logs() {
    LOG_DIR=${LOG_DIR:-/tmp/logs}

    if [ "$CONTAINER_ENGINE" = "docker" ]; then
        VOLUMES_DIR="/var/lib/docker/volumes"
        LOGS_TAIL_PARAMETER="all"
    elif [ "$CONTAINER_ENGINE" = "podman" ]; then
        VOLUMES_DIR="/var/lib/containers/storage/volumes"
        LOGS_TAIL_PARAMETER="-1"
    else
        echo "Invalid container engine: ${CONTAINER_ENGINE}"
        exit 1
    fi
    cp -rL /home/zuul/tempest ${LOG_DIR}/
    [ -d ${VOLUMES_DIR}/kolla_logs/_data ] && cp -rnL ${VOLUMES_DIR}/kolla_logs/_data/* ${LOG_DIR}/kolla/
    [ -d /etc/kolla ] && cp -rnL /etc/kolla/* ${LOG_DIR}/kolla_configs/
    # Don't save the IPA images.
    rm -f ${LOG_DIR}/kolla_configs/config/ironic/ironic-agent.{kernel,initramfs}
    mkdir ${LOG_DIR}/system_configs/
    cp -rL /etc/{hostname,hosts,host.conf,resolv.conf,nsswitch.conf,systemd} ${LOG_DIR}/system_configs/
    # copy docker configs if used
    if [ "$CONTAINER_ENGINE" = "docker" ]; then
        cp -rL /etc/docker/ ${LOG_DIR}/system_configs/
    elif [ "$CONTAINER_ENGINE" = "podman" ]; then
        cp -rL /etc/containers/ ${LOG_DIR}/system_configs/
    fi
    # List all permissions to log files
    ls -lLR /var/log/kolla > ${LOG_DIR}/system_logs/ls_lr_var_log_kolla.txt
    # Remove /var/log/kolla link to not double the data uploaded
    unlink /var/log/kolla
    cp -rvnL /var/log/* ${LOG_DIR}/system_logs/


    if [[ -x "$(command -v journalctl)" ]]; then
        journalctl --no-pager > ${LOG_DIR}/system_logs/syslog.txt
        journalctl --no-pager -u ${CONTAINER_ENGINE}.service > ${LOG_DIR}/system_logs/${CONTAINER_ENGINE}.log
        if [ "$CONTAINER_ENGINE" = "docker" ]; then
            journalctl --no-pager -u containerd.service > ${LOG_DIR}/system_logs/containerd.log
        fi
    fi

    cp -r /etc/sudoers.d ${LOG_DIR}/system_logs/
    cp /etc/sudoers ${LOG_DIR}/system_logs/sudoers.txt

    df -h > ${LOG_DIR}/system_logs/df.txt
    free  > ${LOG_DIR}/system_logs/free.txt
    lsblk > ${LOG_DIR}/system_logs/lsblk.txt
    mount > ${LOG_DIR}/system_logs/mount.txt
    env > ${LOG_DIR}/system_logs/env.txt
    systemctl status > ${LOG_DIR}/system_logs/systemctl_status.txt
    systemctl list-units --all > ${LOG_DIR}/system_logs/systemctl_units.txt
    systemctl list-unit-files > ${LOG_DIR}/system_logs/systemctl_unit_files.txt

    (set -x
    ip a
    ip m
    ip l
    ip r
    ip -6 r
    ip neigh
    ping -c 4 $(hostname)
    ping6 -c 4 $(hostname)
    ping -c 4 ${KOLLA_INTERNAL_VIP_ADDRESS}
    ping6 -c 4 ${KOLLA_INTERNAL_VIP_ADDRESS}) &> ${LOG_DIR}/system_logs/ip.txt

    (set -x
    iptables -t raw -v -n -L
    iptables -t mangle -v -n -L
    iptables -t nat -v -n -L
    iptables -t filter -v -n -L) &> ${LOG_DIR}/system_logs/iptables.txt

    (set -x
    ip6tables -t raw -v -n -L
    ip6tables -t mangle -v -n -L
    ip6tables -t nat -v -n -L
    ip6tables -t filter -v -n -L) &> ${LOG_DIR}/system_logs/ip6tables.txt

    ss -nep > ${LOG_DIR}/system_logs/ss.txt

    ss -nep -l > ${LOG_DIR}/system_logs/ss_l.txt

    (set -x
    getent ahostsv4 $(hostname)
    getent ahostsv6 $(hostname)) &> ${LOG_DIR}/system_logs/getent_ahostsvX.txt

    sysctl -a &> ${LOG_DIR}/system_logs/sysctl.txt
    lsmod &> ${LOG_DIR}/system_logs/lsmod.txt

    if [ `command -v dpkg` ]; then
        dpkg -l > ${LOG_DIR}/system_logs/dpkg-l.txt
    fi
    if [ `command -v rpm` ]; then
        rpm -qa > ${LOG_DIR}/system_logs/rpm-qa.txt
    fi

    # final memory usage and process list
    ps -eo user,pid,ppid,lwp,%cpu,%mem,size,rss,cmd > ${LOG_DIR}/system_logs/ps.txt

    # container engine related information
    [ `command -v ${CONTAINER_ENGINE}` ] &&
    (   ${CONTAINER_ENGINE} info &&
        ${CONTAINER_ENGINE} images &&
        ${CONTAINER_ENGINE} ps -a &&
        ${CONTAINER_ENGINE} network ls &&
        ${CONTAINER_ENGINE} inspect $(${CONTAINER_ENGINE} ps -aq)) > ${LOG_DIR}/system_logs/${CONTAINER_ENGINE}-info.txt

    # save dbus services
    [ `command -v dbus-send` ] && dbus-send --system --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames > ${LOG_DIR}/system_logs/dbus-services.txt

    # cephadm related logs
    if [ `command -v cephadm` ]; then
        mkdir -p ${LOG_DIR}/ceph
        [ -d /etc/ceph ] && sudo cp /etc/ceph/ceph.conf ${LOG_DIR}/ceph
        [ -d /var/run/ceph ] && sudo cp /var/run/ceph/*/cluster.yml ${LOG_DIR}/ceph/cluster.yml
        [ -d /var/log/ceph ] && sudo cp /var/log/ceph/cephadm.log* ${LOG_DIR}/ceph/
        sudo cephadm shell -- ceph --connect-timeout 5 -s > ${LOG_DIR}/ceph/ceph_s.txt
        sudo cephadm shell -- ceph --connect-timeout 5 osd tree > ${LOG_DIR}/ceph/ceph_osd_tree.txt
    fi

    # bifrost related logs
    if [[ $(${CONTAINER_ENGINE} ps --filter name=bifrost_deploy --format "{{.Names}}") ]]; then
        for service in dnsmasq ironic ironic-api ironic-conductor mariadb nginx; do
            mkdir -p ${LOG_DIR}/kolla/$service
            ${CONTAINER_ENGINE} exec bifrost_deploy systemctl status $service > ${LOG_DIR}/kolla/$service/systemd-status-$service.txt
        done
        ${CONTAINER_ENGINE} exec bifrost_deploy journalctl -u mariadb > ${LOG_DIR}/kolla/mariadb/mariadb.txt
    fi

    # haproxy related logs
    if [[ $(${CONTAINER_ENGINE} ps --filter name=haproxy --format "{{.Names}}") ]]; then
        mkdir -p ${LOG_DIR}/kolla/haproxy
        ${CONTAINER_ENGINE} exec haproxy bash -c 'echo show stat | socat stdio /var/lib/kolla/haproxy/haproxy.sock' > ${LOG_DIR}/kolla/haproxy/stats.txt
    fi

    for container in $(${CONTAINER_ENGINE} ps -a --format "{{.Names}}"); do
        ${CONTAINER_ENGINE} logs --timestamps --tail=${LOGS_TAIL_PARAMETER} ${container} &> ${LOG_DIR}/container_logs/${container}.txt
    done

    # Rename files to .txt; this is so that when displayed via
    # logs.openstack.org clicking results in the browser shows the
    # files, rather than trying to send it to another app or make you
    # download it, etc.

    # Rename all .log files to .txt files
    for f in $(find ${LOG_DIR}/{system_logs,kolla,${CONTAINER_ENGINE}_logs} -name "*.log"); do
        mv $f ${f/.log/.txt}
    done

    chmod -R 777 ${LOG_DIR}

    du -sm ${LOG_DIR}
}

copy_logs
