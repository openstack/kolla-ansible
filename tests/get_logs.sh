#!/bin/bash

set +o errexit

copy_logs() {
    LOG_DIR=${LOG_DIR:-/tmp/logs}

    cp -rnL /var/lib/docker/volumes/kolla_logs/_data/* ${LOG_DIR}/kolla/
    cp -rnL /etc/kolla/* ${LOG_DIR}/kolla_configs/
    # Don't save the IPA images.
    rm ${LOG_DIR}/kolla_configs/config/ironic/ironic-agent.{kernel,initramfs}
    mkdir ${LOG_DIR}/system_configs/
    cp -rL /etc/{hostname,hosts,host.conf,resolv.conf,nsswitch.conf,docker,systemd} ${LOG_DIR}/system_configs/
    # Remove /var/log/kolla link to not double the data uploaded
    unlink /var/log/kolla
    cp -rvnL /var/log/* ${LOG_DIR}/system_logs/


    if [[ -x "$(command -v journalctl)" ]]; then
        journalctl --no-pager > ${LOG_DIR}/system_logs/syslog.txt
        journalctl --no-pager -u docker.service > ${LOG_DIR}/system_logs/docker.log
        journalctl --no-pager -u containerd.service > ${LOG_DIR}/system_logs/containerd.log
    else
        cp /var/log/upstart/docker.log ${LOG_DIR}/system_logs/docker.log
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

    # docker related information
    (docker info && docker images && docker ps -a && docker network ls && docker inspect $(docker ps -aq)) > ${LOG_DIR}/system_logs/docker-info.txt

    # save dbus services
    dbus-send --system --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames > ${LOG_DIR}/system_logs/dbus-services.txt

    # cephadm related logs
    mkdir -p ${LOG_DIR}/ceph
    sudo cp /etc/ceph/ceph.conf ${LOG_DIR}/ceph
    sudo cp /var/run/ceph/*/cluster.yml ${LOG_DIR}/ceph/cluster.yml
    sudo cephadm shell -- ceph --connect-timeout 5 -s > ${LOG_DIR}/ceph/ceph_s.txt
    sudo cephadm shell -- ceph --connect-timeout 5 osd tree > ${LOG_DIR}/ceph/ceph_osd_tree.txt

    # bifrost related logs
    if [[ $(docker ps --filter name=bifrost_deploy --format "{{.Names}}") ]]; then
        for service in dnsmasq ironic ironic-api ironic-conductor ironic-inspector mariadb nginx; do
            mkdir -p ${LOG_DIR}/kolla/$service
            docker exec bifrost_deploy systemctl status $service > ${LOG_DIR}/kolla/$service/systemd-status-$service.txt
        done
        docker exec bifrost_deploy journalctl -u mariadb > ${LOG_DIR}/kolla/mariadb/mariadb.txt
    fi

    # haproxy related logs
    if [[ $(docker ps --filter name=haproxy --format "{{.Names}}") ]]; then
        mkdir -p ${LOG_DIR}/kolla/haproxy
        docker exec haproxy bash -c 'echo show stat | socat stdio /var/lib/kolla/haproxy/haproxy.sock' > ${LOG_DIR}/kolla/haproxy/stats.txt
    fi

    # FIXME: remove
    if [[ $(docker ps -a --filter name=ironic_inspector --format "{{.Names}}") ]]; then
        mkdir -p ${LOG_DIR}/kolla/ironic-inspector
        ls -lR /var/lib/docker/volumes/ironic_inspector_dhcp_hosts > ${LOG_DIR}/kolla/ironic-inspector/var-lib-ls.txt
    fi

    for container in $(docker ps -a --format "{{.Names}}"); do
        docker logs --timestamps --tail all ${container} &> ${LOG_DIR}/docker_logs/${container}.txt
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

    du -sm ${LOG_DIR}
}

copy_logs
