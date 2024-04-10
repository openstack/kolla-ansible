#!/usr/bin/env bash

_XTRACE_OVS_DPDK_CTL=$(set +o | grep xtrace)
if [[ "${OVS_DPDK_CTL_DEBUG}" == "True" ]]; then
    set -o xtrace
fi

FULL_PATH=$(realpath "${BASH_SOURCE[0]}")
CONFIG_FILE=${CONFIG_FILE:-"/etc/default/ovs-dpdk.conf"}
SERVICE_FILE="/etc/systemd/system/ovs-dpdkctl.service"
BRIDGE_SERVICE_FILE="/etc/systemd/system/ovs-dpdk-bridge.service"

function get_value {
    crudini --get $CONFIG_FILE $@
}

function set_value {
    crudini --set $CONFIG_FILE $1 $2 "$3"
}

function del_value {
    crudini --del $CONFIG_FILE $@
}

function is_set {
    output=$(crudini --get $CONFIG_FILE $* &> /dev/null ) && [ -n "$(crudini --get $CONFIG_FILE $*)" ]; echo $?
}

function show_config {
    cat $CONFIG_FILE
}

function get_config {
    echo $CONFIG_FILE
}

function del_config {
    rm -f $CONFIG_FILE
}

function is_redhat_family {
    [[ -e /etc/redhat-release ]] ; echo $?
}

function generate_pciwhitelist {
    _Whitelist=''
    for nic in $(list_dpdk_nics); do
        address="$(get_value $nic address)"
        if [ "$_Whitelist" == '' ]; then
            _Whitelist="-a $address"
        else
            _Whitelist="$_Whitelist -a $address"
        fi
    done
    echo $_Whitelist
}

function gen_port_mappings {
    OVS_BRIDGE_MAPPINGS=$(get_value ovs bridge_mappings)
    OVS_BRIDGES=${OVS_BRIDGE_MAPPINGS//,/ }
    OVS_DPDK_PORT_MAPPINGS=""
    ARRAY=( $OVS_BRIDGES )
    for net in "${ARRAY[@]}"; do
        bridge="${net##*:}"
        nic=${bridge/br-/}
        if [[ -z "$OVS_DPDK_PORT_MAPPINGS" ]]; then
            OVS_DPDK_PORT_MAPPINGS="$nic:$bridge"
        else
            OVS_DPDK_PORT_MAPPINGS="$OVS_DPDK_PORT_MAPPINGS,$nic:$bridge"
        fi
    done
    echo "$OVS_DPDK_PORT_MAPPINGS"
}

function gen_config {
    del_config
    touch $CONFIG_FILE
    set_value ovs bridge_mappings ${bridge_mappings:-""}
    set_value ovs port_mappings ${port_mappings:-$(gen_port_mappings)}
    set_value ovs cidr_mappings ${cidr_mappings:-""}
    set_value ovs ovs_coremask ${ovs_coremask:-"0x1"}
    set_value ovs pmd_coremask ${pmd_coremask:-"0x2"}
    set_value ovs ovs_mem_channels ${ovs_mem_channels:-4}
    set_value ovs ovs_socket_mem ${ovs_socket_mem:-"512"}
    set_value ovs dpdk_interface_driver ${dpdk_interface_driver:-"uio_pci_generic"}
    set_value ovs hugepage_mountpoint ${hugepage_mountpoint:-"/dev/hugepages"}
    set_value ovs physical_port_policy ${ovs_physical_port_policy:-"named"}

    ls -al /sys/class/net/* | awk '$0 ~ /pci/ {n=split($NF,a,"/"); print "\n[" a[n] "]\naddress = " a[n-2]  "\ndriver ="}' >> $CONFIG_FILE

    for nic in $(get_value | grep -v ovs); do
        set_value $nic driver $(get_driver_by_address $(get_value $nic address))
    done
    for nic in $(list_dpdk_nics); do
        set_value $nic driver ${dpdk_interface_driver:-"uio_pci_generic"}
    done
    set_value ovs pci_whitelist "${pci_whitelist:-$(generate_pciwhitelist)}"
}

function bind_nic {
    echo $2 > /sys/bus/pci/devices/$1/driver_override
    echo $1 > /sys/bus/pci/drivers/$2/bind
}

function unbind_nic {
    echo $1 > /sys/bus/pci/drivers/$2/unbind
    echo > /sys/bus/pci/devices/$1/driver_override
}

function list_dpdk_nics {
    for nic in $(get_value ovs port_mappings | tr ',' '\n' | cut -d : -f 1); do
        echo $nic;
    done
}

function bind_nics {
    for nic in $(list_dpdk_nics); do
        device_address="$(get_value $nic address)"
        current_driver="$(get_driver_by_address $device_address)"
        target_driver="$(get_value $nic driver)"
        if [ "$current_driver" != "$target_driver" ]; then
            set_value $nic old_driver $current_driver
            unbind_nic $device_address $current_driver
            bind_nic $device_address $target_driver
        fi
    done
}

function unbind_nics {
    for nic in $(list_dpdk_nics); do
        if [ "$(is_set $nic old_driver)" == 0 ]; then
            device_address="$(get_value $nic address)"
            current_driver="$(get_driver_by_address $device_address)"
            target_driver="$(get_value $nic old_driver)"
            if [ "$current_driver" != "$target_driver" ]; then
                unbind_nic $device_address $current_driver
                bind_nic $device_address $target_driver
                del_value $nic old_driver
            fi
        fi
    done
}

function get_address_by_name {
    ls -al /sys/class/net/$1 | awk '$0 ~ /pci/ {n=split($NF,a,"/"); print a[n-2] }'
}

function get_driver_by_address {
    ls /sys/bus/pci/devices/$1/driver -al | awk '{n=split($NF,a,"/"); print a[n]}'
}

function get_port_bridge {
    for pair in $(get_value ovs port_mappings | tr ',' '\n'); do
        nic=`echo $pair | cut -f 1 -d ":"`
        if [[ "$nic" == "$1" ]]; then
            bridge=`echo $pair | cut -f 2 -d ":"`
            echo $bridge
            return 0
        fi
    done
    return 1
}

function init_ovs_db {
    ovs-vsctl init
    ovs-vsctl --no-wait set Open_vSwitch . other_config:pmd-cpu-mask="$(get_value ovs pmd_coremask)" \
    other_config:dpdk-init=True other_config:dpdk-lcore-mask="$(get_value ovs ovs_coremask)" \
    other_config:dpdk-mem-channels="$(get_value ovs ovs_mem_channels)" \
    other_config:dpdk-socket-mem="$(get_value ovs ovs_socket_mem)" \
    other_config:dpdk-hugepage-dir="$(get_value ovs hugepage_mountpoint)"  \
    other_config:dpdk-extra=" --proc-type primary $(get_value ovs pci_whitelist) "
}

function init_ovs_bridges {
    raw_bridge_mappings=$(get_value ovs bridge_mappings)
    bridge_mappings=( ${raw_bridge_mappings//,/ } )
    for pair in "${bridge_mappings[@]}"; do
        bridge=`echo $pair | cut -f 2 -d ":"`
        sudo ovs-vsctl --no-wait -- --may-exist add-br $bridge -- set Bridge $bridge datapath_type=netdev
    done
}

function init_ovs_interfaces {
    pci_port_pairs=''
    for nic in $(list_dpdk_nics); do
        address="$(get_value $nic address)"
        if [ "$pci_port_pairs" == '' ]; then
            pci_port_pairs="$address,$nic"
        else
            pci_port_pairs="$pci_port_pairs $address,$nic"
        fi
    done
    pci_port_pairs="$(echo $pci_port_pairs | sort)"
    dpdk_port_number=0
    for pair in  $pci_port_pairs; do
        addr="$(echo $pair | cut -f 1 -d ",")"
        nic="$(echo $pair | cut -f 2 -d ",")"
        bridge="$(get_port_bridge $nic)"
        # ovs 2.6 and older requires dpdkX names, ovs 2.7+ requires dpdk-devargs instead.
        if [ "$(get_value ovs physical_port_policy)" == "indexed" ]; then
            ovs-vsctl --no-wait --may-exist add-port $bridge "dpdk${dpdk_port_number}" \
            -- set Interface  "dpdk${dpdk_port_number}" type=dpdk
        else
            ovs-vsctl --may-exist add-port $bridge $nic \
            -- set Interface  $nic type=dpdk options:dpdk-devargs=$addr
        fi

        dpdk_port_number=$((dpdk_port_number+1))
    done
}

function init {
    init_ovs_db
    init_ovs_bridges
    init_ovs_interfaces
}

function install_network_manager_conf {
    pair=$(get_value ovs cidr_mappings)
    bridge=`echo $pair | cut -f 1 -d ":"`
    cidr=`echo $pair | cut -f 2 -d ":"`
    ip=`echo $cidr | cut -f 1 -d "/"`
    prefix=`echo $cidr | cut -f 2 -d "/"`
    mask=""
    full_octets=$(expr $prefix / 8)
    partial_octet=$(expr $prefix % 8)

    for octet in 0 1 2 3 ; do
        if [[ "$octet" < "$full_octets" ]]; then
            mask+=255
        elif [[ "$octet" == "$full_octets" ]]; then
            mask+=$((256 - 2**(8-$partial_octet)))
        else
            mask+=0
        fi
        [[ "$octet" < 3 ]] && mask+=.
    done
    if  [[ $(is_redhat_family) == 0 ]]; then
        cat << EOF | tee "/etc/sysconfig/network-scripts/ifcfg-$bridge"
DEVICE=$bridge
BOOTPROTO=static
IPADDR=$ip
NETMASK=$mask
HOTPLUG=yes
ONBOOT=yes
NM_CONTROLLED=no
EOF
install_redhat_bridge_service $bridge
    else
        cat << EOF | tee "/etc/network/interfaces.d/$bridge.cfg"
    auto $bridge
    iface $bridge inet static
        address $ip
        netmask $mask
EOF

    fi
}

function uninstall_network_manager_conf {
    pair=$(get_value ovs cidr_mappings)
    bridge=`echo $pair | cut -f 1 -d ":"`
    if  [[ $(is_redhat_family) == 0 ]]; then
        rm -f /etc/sysconfig/network-scripts/ifcfg-$bridge
    else
        rm -f /etc/network/interfaces.d/$bridge.cfg
    fi
}

function install_service {
    cat << EOF | tee "$SERVICE_FILE"

[Unit]
Description=configuration service for ovs-dpdk nics.
Before=network-pre.target
After=syslog.target

[Service]
# Uncomment to enable debug logging.
# Environment=OVS_DPDK_CTL_DEBUG=True
Environment=CONFIG_FILE=$CONFIG_FILE
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/ovs-dpdkctl bind_nics
ExecStop=/bin/ovs-dpdkctl unbind_nics

[Install]
WantedBy=multi-user.target

EOF
    systemctl daemon-reload
    systemctl enable ovs-dpdkctl
}

function install_redhat_bridge_service {
    cat << EOF | tee "$BRIDGE_SERVICE_FILE"
[Unit]
Description=configuration service for ovs-dpdk bridge.
After=docker.service
After=network.target
After=ovs-dpdkctl.service

[Service]
Type=simple
RemainAfterExit=yes
ExecStartPre=/bin/bash -c "[[ -e /sys/class/net/$1 ]]"
ExecStart=/usr/sbin/ifup $1
ExecStop=/usr/sbin/ifdown $1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target

EOF
    systemctl daemon-reload
    systemctl enable ovs-dpdk-bridge
}

function uninstall_service {
    systemctl disable ovs-dpdkctl
    rm -f "$SERVICE_FILE"
    if [ -e "$BRIDGE_SERVICE_FILE" ]; then
        systemctl disable ovs-dpdk-bridge
        rm -f "$BRIDGE_SERVICE_FILE"
    fi
    systemctl daemon-reload
}

function configure_kernel_modules {
    driver="$(get_value ovs dpdk_interface_driver)"
    lsmod | grep -ws $driver > /dev/null || modprobe $driver
    if  [[ $(is_redhat_family) == 0 ]]; then
        [[ ! -e /etc/modules-load.d/${driver}.conf ]] && echo $driver | tee /etc/modules-load.d/${driver}.conf
    else
        grep -ws $driver /etc/modules > /dev/null || echo $driver | tee -a /etc/modules
    fi
}

function unconfigure_kernel_modules {
    driver="$(get_value ovs dpdk_interface_driver)"
    lsmod | grep -ws $driver > /dev/null && rmmod $driver
    if [[ $(is_redhat_family) == 0 ]] ; then
        [[ -e /etc/modules-load.d/${driver}.conf ]] && rm -f /etc/modules-load.d/${driver}.conf
    else
        grep  -ws $driver /etc/modules > /dev/null && sed -e "s/$driver//" -i /etc/modules
    fi
}

function install {
    if [ ! -e "$CONFIG_FILE" ]; then
        gen_config
    fi
    configure_kernel_modules
    if [ ! -e "$SERVICE_FILE" ]; then
        install_service
    fi
    if [ ! -e /bin/ovs-dpdkctl ]; then
        cp "$FULL_PATH" /bin/ovs-dpdkctl
        chmod +x /bin/ovs-dpdkctl
    fi
    systemctl start ovs-dpdkctl
    install_network_manager_conf
    if  [[ $(is_redhat_family) == 0 ]]; then
        systemctl start ovs-dpdk-bridge
    fi
}

function uninstall {
    systemctl stop ovs-dpdkctl
    if [ -e "$SERVICE_FILE" ]; then
        uninstall_service
    fi
    uninstall_network_manager_conf
    unconfigure_kernel_modules
    if [ -e /bin/ovs-dpdkctl ]; then
        rm -f /bin/ovs-dpdkctl
    fi
    if [ -e "$CONFIG_FILE" ]; then
        rm -f "$CONFIG_FILE"
    fi
}

function usage {
    cat << "EOF"
ovs-dpdkctl.sh: A tool to configure ovs with dpdk.

- This tool automate the process of binding host insterfacesto a dpdk
  compatible driver (uio_pci_generic | vfio-pci) at boot.
- This tool automate bootstrapping ovs so that it can use the
  dpdk accelerated netdev datapath.

commands:
  - install:
    - installs ovs-dpdkctl as a systemd service.
    - installs ovs-dpdkctl binary.
    - generates ovs-dpdkctl configuration file.
    - starts ovs-dpdkctl service.
  - uninstall:
    - stops ovs-dpdkctl service.
    - uninstalls ovs-dpdkctl systemd service.
    - uninstalls ovs-dpdkctl binary.
    - removes ovs-dpdkctl configuration file.
  - bind_nics:
    - iterates over all dpdk interfaces defined in ovs-dpdkctl config
      and binds the interface to the target driver specified in the config
      if current driver does not equal target.
  - unbind_nics:
    - iterates over all dpdk interfaces defined in ovs-dpdkctl config
      and restores the interface to its original non dpdk driver.
  - init:
    - defines dpdk specific configuration parameter in the ovsdb.
    - creates bridges as specified by ovs bridge_mappings in
      ovs-dpdkctl config.
    - creates dpdk ports as defined by ovs port_mappings in
      ovs-dpdkctl config.
  - usage:
    - prints this message

options:
  - debugging:
    - To enable debugging export OVS_DPDK_CTL_DEBUG=True
  - install:
    - The variables described below can be defined to customise
      installation of ovs-dpdkctl.
      <variable>=<value> ovs-dpdkctl.sh install
    - bridge_mappings:
      - A comma separated list of physnet to bridge mappings.
      - Example: bridge_mappings=physnet1:br-ex1,physnet2:br-ex2
      - Default: ""
    - port_mappings:
      - A comma separated list of port to bridge mappings.
      - Example: port_mappings=eth1:br-ex1,eth2:br-ex2
      - Default: generated form bridge_mappings assuming bridge names
                 are constructed by appending br- to port name.
    - cidr_mappings:
      - A comma separated list of bridge to cidr mappings.
      - Example: cidr_mappings=br-ex1:192.168.1.1/24,br-ex2:192.168.2.1/24
      - Default: ""
    - ovs_coremask:
      - A hex encoded string container a bitmask of what cpu core
        to pin the non dataplane treads of the ovs-vswitchd to.
      - Node that only the first core of the bit mask is currently
        used by ovs.
      - Example: ovs_coremask=0x1
      - Default: "0x1"
    - pmd_coremask:
      - A hex encoded string container a bitmask of what cpu cores
        to pin the dataplane pool mode driver treads of the ovs-vswitchd to.
      - Each bit set in the bitmask will result in the creating of a pmd.
      - For best performance it is recommended to allocate at least 1 pmd per
        numa node. On systems with HyperThreading enabled it is recommended to also
        allocate the HT sibling core in the pmd_coremask.cores allocated
        to ovs with dpdk via the pmd_coremask should be removed from the
        nova vcpu_pin_set and isolated from the kernel scheduler.
      - Note it is not recommended to isolate cores in the nova vcpu_pin_set
        unless the host will be dedicated for vms that request cpu pinning.
      - Example: pmd_coremask=0x4
      - Default: "0x4"
    - ovs_mem_channels:
      - The number of memory channels supported by the plathforms.
      - Example: ovs_mem_channels=2
      - Default: "4"
    - ovs_socket_mem:
      - A comma separated list of hugepage memory, specified in MBs per numa node,
        allocated to the ovs-vswitchd to use for the dpdk dataplane.
      - For best performance memory should be allocated evenly across all numa node
        that will run a pmd.
      - Example: ovs_socket_mem=512,512
      - Default: "512"
    - hugepage_mountpoint:
      - The hugepage mountpoint to use when allocating memory for dpdk.
      - Example: hugepage_mountpoint=/dev/my_custom_mountpoint
      - Default: "/dev/hugepages"
    - dpdk_interface_driver:
      - The dpdk compatible userspace driver to use when binding host interfaces.
      - Example: dpdk_interface_driver=vfio_pci
      - Default: "uio_pci_generic"
    - pci_whitelist:
      - A repeated space separated list of pci whitelist flags
        for allowed ovs-dpdk ports.
      - The pci_whitelist allows multiple dpdk primary process to
        utilise different pci devices without resulting in a conflict
        of ownership.
      - Example: pci_whitelist="-a <pci address 1> -a <pci address 2>"
      - Default: auto generated form port_mappings.
EOF

}

if [ $# -ge  1 ]; then
    func=$1
    shift
else
    func="usage"
fi

#replace with switch later
eval "$func $@"


${_XTRACE_OVS_DPDK_CTL}
