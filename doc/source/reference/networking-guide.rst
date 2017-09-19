.. _networking-guide:

==========================
Enabling Provider Networks
==========================
Provider networks allow to connect compute instances directly to physical
networks avoiding tunnels. This is necessary for example for some performance
critical applications. Only administrators of OpenStack can create such
networks. For provider networks compute hosts must have external bridge
created and configured by Ansible tasks like it is already done for tenant
DVR mode networking. Normal tenant non-DVR networking does not need external
bridge on compute hosts and therefore operators don't need additional
dedicated network interface.

To enable provider networks modify the configuration
file ``/etc/kolla/globals.yml``:

::

    enable_neutron_provider_networks: "yes"

===========================
Enabling Neutron Extensions
===========================

Overview
========
Kolla deploys Neutron by default as OpenStack networking component. This guide
describes configuring and running Neutron extensions like LBaaS,
Networking-SFC, QoS, etc.

Networking-SFC
==============

Preparation and deployment
--------------------------

Modify the configuration file ``/etc/kolla/globals.yml`` and change
the following:

::

    enable_neutron_sfc: "yes"

Verification
------------

For setting up a testbed environment and creating a port chain, please refer
to `networking-sfc documentation <https://docs.openstack.org/networking-sfc/latest/contributor/system_design_and_workflow.html>`_:

Neutron VPNaaS (VPN-as-a-Service)
=================================

Preparation and deployment
--------------------------

Modify the configuration file ``/etc/kolla/globals.yml`` and change
the following:

::

    enable_neutron_vpnaas: "yes"

Verification
------------

VPNaaS is a complex subject, hence this document provides directions for a
simple smoke test to verify the service is up and running.

On the network node(s), the ``neutron_vpnaas_agent`` should be up (image naming
and versioning may differ depending on deploy configuration):

::

    docker ps --filter name=neutron_vpnaas_agent
    CONTAINER ID        IMAGE
    COMMAND             CREATED             STATUS              PORTS
    NAMES
    97d25657d55e
    operator:5000/kolla/oraclelinux-source-neutron-vpnaas-agent:4.0.0
    "kolla_start"       44 minutes ago      Up 44 minutes
    neutron_vpnaas_agent

Kolla-Ansible includes a small script that can be used in tandem with
``tools/init-runonce`` to verify the VPN using two routers and two Nova VMs:

::

    tools/init-runonce
    tools/init-vpn

Verify both VPN services are active:

::

    neutron vpn-service-list
    +--------------------------------------+----------+--------------------------------------+--------+
    | id                                   | name     | router_id                            | status |
    +--------------------------------------+----------+--------------------------------------+--------+
    | ad941ec4-5f3d-4a30-aae2-1ab3f4347eb1 | vpn_west | 051f7ce3-4301-43cc-bfbd-7ffd59af539e | ACTIVE |
    | edce15db-696f-46d8-9bad-03d087f1f682 | vpn_east | 058842e0-1d01-4230-af8d-0ba6d0da8b1f | ACTIVE |
    +--------------------------------------+----------+--------------------------------------+--------+

Two VMs can now be booted, one on vpn_east, the other on vpn_west, and
encrypted ping packets observed being sent from one to the other.

For more information on this and VPNaaS in Neutron refer to the VPNaaS area on
the OpenStack wiki:

    https://wiki.openstack.org/wiki/Neutron/VPNaaS/HowToInstall
    https://wiki.openstack.org/wiki/Neutron/VPNaaS

Networking-ODL
==============

Preparation and deployment
--------------------------

Modify the configuration file ``/etc/kolla/globals.yml`` and enable
the following:

::

    enable_opendaylight: "yes"

Networking-ODL is an additional Neutron plugin that allows the OpenDaylight
SDN Controller to utilize its networking virtualization features.
For OpenDaylight to work, the Networking-ODL plugin has to be installed in
the ``neutron-server`` container. In this case, one could use the
neutron-server-opendaylight container and the opendaylight container by
pulling from Kolla dockerhub or by building them locally.

OpenDaylight globals.yml configurable options with their defaults include:
::

    opendaylight_release: "0.6.1-Carbon"
    opendaylight_mechanism_driver: "opendaylight_v2"
    opendaylight_l3_service_plugin: "odl-router_v2"
    opendaylight_acl_impl: "learn"
    enable_opendaylight_qos: "no"
    enable_opendaylight_l3: "yes"
    enable_opendaylight_legacy_netvirt_conntrack: "no"
    opendaylight_port_binding_type: "pseudo-agentdb-binding"
    opendaylight_features: "odl-mdsal-apidocs,odl-netvirt-openstack"
    opendaylight_allowed_network_types: '"flat", "vlan", "vxlan"'

Clustered OpenDaylight Deploy
-----------------------------
High availability clustered OpenDaylight requires modifying the inventory file
and placing three or more hosts in the OpenDaylight or Networking groups.
Note: The OpenDaylight role will allow deploy of one or three plus hosts for
OpenDaylight/Networking role.

Verification
------------

Verify the build and deploy operation of Networking-ODL containers. Successful
deployment will bring up an Opendaylight container in the list of running
containers on network/opendaylight node.

For the source code, please refer to the following link:

    https://github.com/openstack/networking-odl


OVS with DPDK
=============

Introduction
------------

Open vSwitch (ovs) is an open source software virtual switch developed
and distributed via openvswitch.org.
The Data Plane Development Kit (dpdk) is a collection of userspace
libraries and tools that facilitate the development of high-performance
userspace networking applications.

As of the ovs 2.2 release, the ovs netdev datapath has supported integration
with dpdk for accelerated userspace networking. As of the pike release
of kolla support for deploying ovs with dpdk (ovs-dpdk) has been added
to kolla ansible. The ovs-dpdk role introduced in the pike release has been
tested on centos 7 and ubuntu 16.04 hosts, however, ubuntu is recommended due
to conflicts with the cgroup configuration created by the default systemd
version shipped with centos 7.

Prerequisites
-------------

DPDK is a high-performance userspace networking library, as such it has
several requirements to function correctly that are not required when
deploying ovs without dpdk.

To function efficiently one of the mechanisms dpdk uses to accelerate
memory access is the utilisation of kernel hugepages. The use of hugepage
memory minimises the chance of a translation lookaside buffer(TLB) miss when
translating virtual to physical memory as it increases the total amount of
addressable memory that can be cached via the TLB. Hugepage memory pages are
unswappable contiguous blocks of memory of typically 2MiB or 1GiB in size,
that can be used to facilitate efficient sharing of memory between guests and
a vSwitch or DMA mapping between physical nics and the userspace ovs datapath.

To deploy ovs-dpdk on a platform a proportion of system memory should
be allocated hugepages. While it is possible to allocate hugepages at runtime
it is advised to allocate them via the kernel command line instead to prevent
memory fragmentation. This can be achieved by adding the following to the grub
config and regenerating your grub file.

::

    default_hugepagesz=2M hugepagesz=2M hugepages=25000


As dpdk is a userspace networking library it requires userspace compatible
drivers to be able to control the physical interfaces on the platform.
dpdk technically support 3 kernel drivers igb_uio,uio_pci_generic and vfio_pci.
While it is technically possible to use all 3 only uio_pci_generic and vfio_pci
are recommended for use with kolla. igb_uio is BSD licenced and distributed
as part of the dpdk library. While it has some advantages over uio_pci_generic
loading the igb_uio module will taint the kernel and possibly invalidate
distro support. To successfully deploy ovs-dpdk, vfio_pci or uio_pci_generic
kernel module must be present on the platform. Most distros include vfio_pci
or uio_pci_generic as part of the default kernel though on some distros you
may need to install kernel-modules-extra or the distro equivalent prior to
running kolla-ansible deploy.

Install
-------

To enable ovs-dpdk add the following to /etc/kolla/globals.yml

::

    ovs_datapath: "netdev"
    enable_ovs_dpdk: yes
    enable_openvswitch: yes
    tunnel_interface: "dpdk_bridge"
    neutron_bridge_name: "dpdk_bridge"

Unlike standard Open vSwitch deployments, the interface specified by
neutron_external_interface should have an ip address assigned.
The ip address assigned to neutron_external_interface will be moved to
the "dpdk_bridge" as part of deploy action.
When using ovs-dpdk the tunnel_interface must be an ovs bridge with a physical
interfaces attached for tunnelled traffic to be accelerated by dpdk.
Note that due to a limitation in ansible variable names which excluded
the use of - in a variable name it is not possible to use the default
br-ex name for the neutron_bridge_name or tunnel_interface.

At present, the tunnel interface ip is configured using network manager on
on ubuntu and systemd on centos family operating systems. systemd is used
to work around a limitation of the centos network manager implementation which
does not consider the creation of an ovs bridge to be a hotplug event. In
the future, a new config option will be introduced to allow systemd to be used
on all host distros for those who do not wish to enable the network manager
service on ubuntu.

To manage ovs-dpdk the neutron ovs agent must be configured to use
the netdev datapath_type in the ml2.conf. At present this is not automated
and must be set via kolla's external config support. To set the datapath_type
create a file with the following content at
/etc/kolla/config/neutron/ml2_conf.ini

::

    [ovs]
    datapath_type = netdev


In the future, the requirement to use the external config will be removed by
automatically computing the value of ovs_datapath based on the value of
enable_ovs_dpdk and then using the ovs_datapath variable to template out this
setting in the ml2_conf.ini automatically.

Limitations
-----------

Reconfiguration from kernel ovs to ovs dpdk is currently not supported.
Changing ovs datapaths on a deployed node requires neutron config changes
and libvirt xml changes for all running instances including a hard reboot
of the vm.

When upgrading ovs-dpdk it should be noted that this will always involve
a dataplane outage. Unlike kernel OVS the dataplane for ovs-dpdk executes in
the ovs-vswitchd process. This means the lifetime of the dpdk dataplane is
tied to the lifetime of the ovsdpdk_vswitchd container. As such it is
recommended to always evacuate all vm workloads from a node running ovs-dpdk
prior to upgrading.

On ubuntu network manager is required for tunnel networking.
This requirement will be removed in the future.
