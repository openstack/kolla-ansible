.. _networking-guide:

===================
Networking in Kolla
===================

Kolla deploys Neutron by default as OpenStack networking component.
This section describes configuring and running Neutron extensions like
LBaaS, Networking-SFC, QoS, and so on.

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

To enable provider networks, modify the ``/etc/kolla/globals.yml`` file
as the following example shows:

.. code-block:: yaml

   enable_neutron_provider_networks: "yes"

.. end

Enabling Neutron Extensions
===========================

Networking-SFC
~~~~~~~~~~~~~~

Preparation and deployment
--------------------------

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_neutron_sfc: "yes"

.. end

Verification
------------

For setting up a testbed environment and creating a port chain, please refer
to `networking-sfc documentation
<https://docs.openstack.org/networking-sfc/latest/contributor/system_design_and_workflow.html>`__.

Neutron VPNaaS (VPN-as-a-Service)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Preparation and deployment
--------------------------

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_neutron_vpnaas: "yes"

.. end

Verification
------------

VPNaaS is a complex subject, hence this document provides directions for a
simple smoke test to verify the service is up and running.

On the network node(s), the ``neutron_vpnaas_agent`` should be up (image naming
and versioning may differ depending on deploy configuration):

.. code-block:: console

   # docker ps --filter name=neutron_vpnaas_agent

   CONTAINER ID   IMAGE                                                               COMMAND         CREATED          STATUS        PORTS  NAMES
   97d25657d55e   operator:5000/kolla/oraclelinux-source-neutron-vpnaas-agent:4.0.0   "kolla_start"   44 minutes ago   Up 44 minutes        neutron_vpnaas_agent

.. end

Kolla-Ansible includes a small script that can be used in tandem with
``tools/init-runonce`` to verify the VPN using two routers and two Nova VMs:

.. code-block:: console

   tools/init-runonce
   tools/init-vpn

.. end

Verify both VPN services are active:

.. code-block:: console

   # neutron vpn-service-list

   +--------------------------------------+----------+--------------------------------------+--------+
   | id                                   | name     | router_id                            | status |
   +--------------------------------------+----------+--------------------------------------+--------+
   | ad941ec4-5f3d-4a30-aae2-1ab3f4347eb1 | vpn_west | 051f7ce3-4301-43cc-bfbd-7ffd59af539e | ACTIVE |
   | edce15db-696f-46d8-9bad-03d087f1f682 | vpn_east | 058842e0-1d01-4230-af8d-0ba6d0da8b1f | ACTIVE |
   +--------------------------------------+----------+--------------------------------------+--------+

.. end

Two VMs can now be booted, one on vpn_east, the other on vpn_west, and
encrypted ping packets observed being sent from one to the other.

For more information on this and VPNaaS in Neutron refer to the
`Neutron VPNaaS Testing <https://docs.openstack.org/neutron-vpnaas/latest/contributor/index.html#testing>`__
and the `OpenStack wiki <https://wiki.openstack.org/wiki/Neutron/VPNaaS>`_.

Networking-ODL
~~~~~~~~~~~~~~

Preparation and deployment
--------------------------

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_opendaylight: "yes"

.. end

Networking-ODL is an additional Neutron plugin that allows the OpenDaylight
SDN Controller to utilize its networking virtualization features.
For OpenDaylight to work, the Networking-ODL plugin has to be installed in
the ``neutron-server`` container. In this case, one could use the
neutron-server-opendaylight container and the opendaylight container by
pulling from Kolla dockerhub or by building them locally.

OpenDaylight ``globals.yml`` configurable options with their defaults include:

.. code-block:: yaml

   opendaylight_mechanism_driver: "opendaylight_v2"
   opendaylight_l3_service_plugin: "odl-router_v2"
   opendaylight_acl_impl: "learn"
   enable_opendaylight_qos: "no"
   enable_opendaylight_l3: "yes"
   enable_opendaylight_legacy_netvirt_conntrack: "no"
   opendaylight_port_binding_type: "pseudo-agentdb-binding"
   opendaylight_features: "odl-mdsal-apidocs,odl-netvirt-openstack"
   opendaylight_allowed_network_types: '"flat", "vlan", "vxlan"'

.. end

Clustered OpenDaylight Deploy
-----------------------------

High availability clustered OpenDaylight requires modifying the inventory file
and placing three or more hosts in the OpenDaylight or Networking groups.

.. note::

   The OpenDaylight role will allow deploy of one or three plus hosts for
   OpenDaylight/Networking role.

Verification
------------

Verify the build and deploy operation of Networking-ODL containers. Successful
deployment will bring up an Opendaylight container in the list of running
containers on network/opendaylight node.

For the source code, please refer to the following link:
https://github.com/openstack/networking-odl

OVS with DPDK
~~~~~~~~~~~~~

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

.. code-block:: console

   default_hugepagesz=2M hugepagesz=2M hugepages=25000

.. end

As dpdk is a userspace networking library it requires userspace compatible
drivers to be able to control the physical interfaces on the platform.
dpdk technically support 3 kernel drivers ``igb_uio``,``uio_pci_generic``, and
``vfio_pci``.
While it is technically possible to use all 3 only ``uio_pci_generic`` and
``vfio_pci`` are recommended for use with kolla. ``igb_uio`` is BSD licenced
and distributed as part of the dpdk library. While it has some advantages over
``uio_pci_generic`` loading the ``igb_uio`` module will taint the kernel and
possibly invalidate distro support. To successfully deploy ``ovs-dpdk``,
``vfio_pci`` or ``uio_pci_generic`` kernel module must be present on the
platform. Most distros include ``vfio_pci`` or ``uio_pci_generic`` as part of
the default kernel though on some distros you may need to install
``kernel-modules-extra`` or the distro equivalent prior to running
:command:`kolla-ansible deploy`.

Installation
------------

To enable ovs-dpdk, add the following configuration to
``/etc/kolla/globals.yml`` file:

.. code-block:: yaml

   ovs_datapath: "netdev"
   enable_ovs_dpdk: yes
   enable_openvswitch: yes
   tunnel_interface: "dpdk_bridge"
   neutron_bridge_name: "dpdk_bridge"

.. end

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

Neutron SRIOV
~~~~~~~~~~~~~

Preparation and deployment
--------------------------

SRIOV requires specific NIC and BIOS configuration and is not supported on all
platforms. Consult NIC and platform specific documentation for instructions
on enablement.

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_neutron_sriov: "yes"

.. end

Modify the ``/etc/kolla/config/neutron/ml2_conf.ini`` file and add
``sriovnicswitch`` to the ``mechanism_drivers``. Also, the provider
networks used by SRIOV should be configured. Both flat and VLAN are configured
with the same physical network name in this example:

.. path /etc/kolla/config/neutron/ml2_conf.ini
.. code-block:: ini

   [ml2]
   mechanism_drivers = openvswitch,l2population,sriovnicswitch

   [ml2_type_vlan]
   network_vlan_ranges = sriovtenant1:1000:1009

   [ml2_type_flat]
   flat_networks = sriovtenant1

.. end

Add ``PciPassthroughFilter`` to scheduler_default_filters

The ``PciPassthroughFilter``, which is required by Nova Scheduler service
on the Controller, should be added to ``scheduler_default_filters``

Modify the ``/etc/kolla/config/nova.conf`` file and add
``PciPassthroughFilter`` to ``scheduler_default_filters``. this filter is
required by The Nova Scheduler service on the controller node.

.. path /etc/kolla/config/nova.conf
.. code-block:: ini

   [DEFAULT]
   scheduler_default_filters = <existing filters>, PciPassthroughFilter
   scheduler_available_filters = nova.scheduler.filters.all_filters

.. end

Edit the ``/etc/kolla/config/nova.conf`` file and add PCI device whitelisting.
this is needed by OpenStack Compute service(s) on the Compute.

.. path /etc/kolla/config/nova.conf
.. code-block:: ini

   [pci]
   passthrough_whitelist = [{"devname": "ens785f0", "physical_network": "sriovtenant1"}]

.. end

Modify the ``/etc/kolla/config/neutron/sriov_agent.ini`` file. Add physical
network to interface mapping. Specific VFs can also be excluded here. Leaving
blank means to enable all VFs for the interface:

.. path /etc/kolla/config/neutron/sriov_agent.ini
.. code-block:: ini

   [sriov_nic]
   physical_device_mappings = sriovtenant1:ens785f0
   exclude_devices =

.. end

Run deployment.

Verification
------------

Check that VFs were created on the compute node(s). VFs will appear in the
output of both ``lspci`` and ``ip link show``.  For example:

.. code-block:: console

   # lspci | grep net
   05:10.0 Ethernet controller: Intel Corporation 82599 Ethernet Controller Virtual Function (rev 01)


   # ip -d link show ens785f0
   4: ens785f0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq master ovs-system state UP mode DEFAULT qlen 1000
   link/ether 90:e2:ba:ba:fb:20 brd ff:ff:ff:ff:ff:ff promiscuity 1
   openvswitch_slave addrgenmode eui64
   vf 0 MAC 52:54:00:36:57:e0, spoof checking on, link-state auto, trust off
   vf 1 MAC 52:54:00:00:62:db, spoof checking on, link-state auto, trust off
   vf 2 MAC fa:16:3e:92:cf:12, spoof checking on, link-state auto, trust off
   vf 3 MAC fa:16:3e:00:a3:01, vlan 1000, spoof checking on, link-state auto, trust off

.. end

Verify the SRIOV Agent container is running on the compute node(s):

.. code-block:: console

   # docker ps --filter name=neutron_sriov_agent
   CONTAINER ID   IMAGE                                                                COMMAND        CREATED         STATUS         PORTS  NAMES
   b03a8f4c0b80   10.10.10.10:4000/registry/centos-source-neutron-sriov-agent:17.04.0  "kolla_start"  18 minutes ago  Up 18 minutes         neutron_sriov_agent

.. end

Verify the SRIOV Agent service is present and UP:

.. code-block:: console

   # openstack network agent list

   +--------------------------------------+--------------------+-------------+-------------------+-------+-------+---------------------------+
   | ID                                   | Agent Type         | Host        | Availability Zone | Alive | State | Binary                    |
   +--------------------------------------+--------------------+-------------+-------------------+-------+-------+---------------------------+
   | 7c06bda9-7b87-487e-a645-cc6c289d9082 | NIC Switch agent   | av09-18-wcp | None              | :-)   | UP    | neutron-sriov-nic-agent   |
   +--------------------------------------+--------------------+-------------+-------------------+-------+-------+---------------------------+

.. end

Create a new provider network. Set ``provider-physical-network`` to the
physical network name that was configured in ``/etc/kolla/config/nova.conf``.
Set ``provider-network-type`` to the desired type. If using VLAN, ensure
``provider-segment`` is set to the correct VLAN ID. This example uses ``VLAN``
network type:


.. code-block:: console

   # openstack network create --project=admin \
     --provider-network-type=vlan \
     --provider-physical-network=sriovtenant1 \
     --provider-segment=1000 \
     sriovnet1

Create a subnet with a DHCP range for the provider network:

.. code-block:: console

   # openstack subnet create --network=sriovnet1 \
     --subnet-range=11.0.0.0/24 \
     --allocation-pool start=11.0.0.5,end=11.0.0.100 \
     sriovnet1_sub1

.. end

Create a port on the provider network with ``vnic_type`` set to ``direct``:

.. code-block:: console

   # openstack port create --network sriovnet1 --vnic-type=direct sriovnet1-port1

.. end

Start a new instance with the SRIOV port assigned:

.. code-block:: console

   # openstack server create --flavor flavor1 \
     --image fc-26 \
     --nic port-id=`openstack port list | grep sriovnet1-port1 | awk '{print $2}'` \
     vm1

Verify the instance boots with the SRIOV port. Verify VF assignment by running
dmesg on the compute node where the instance was placed.

.. code-block:: console

   # dmesg
   [ 2896.849970] ixgbe 0000:05:00.0: setting MAC fa:16:3e:00:a3:01 on VF 3
   [ 2896.850028] ixgbe 0000:05:00.0: Setting VLAN 1000, QOS 0x0 on VF 3
   [ 2897.403367] vfio-pci 0000:05:10.4: enabling device (0000 -> 0002)

.. end

For more information see `OpenStack SRIOV documentation <https://docs.openstack.org/neutron/rocky/admin/config-sriov.html>`_.

Nova SRIOV
~~~~~~~~~~

Preparation and deployment
--------------------------

Nova provides a separate mechanism to attach PCI devices to instances that
is independent from Neutron.  Using the PCI alias configuration option in
nova.conf, any PCI device (PF or VF) that supports passthrough can be attached
to an instance.  One major drawback to be aware of when using this method is
that the PCI alias option uses a device's product id and vendor id only,
so in environments that have NICs with multiple ports configured for SRIOV,
it is impossible to specify a specific NIC port to pull VFs from.

Modify the file ``/etc/kolla/config/nova.conf``.  The Nova Scheduler service
on the control node requires the ``PciPassthroughFilter`` to be added to the
list of filters and the Nova Compute service(s) on the compute node(s) need
PCI device whitelisting.  The Nova API service on the control node and the Nova
Compute service on the compute node also require the ``alias`` option under the
``[pci]`` section.  The alias can be configured as 'type-VF' to pass VFs or
'type-PF' to pass the PF. Type-VF is shown in this example:

.. path /etc/kolla/config/nova.conf
.. code-block:: ini

   [DEFAULT]
   scheduler_default_filters = <existing filters>, PciPassthroughFilter
   scheduler_available_filters = nova.scheduler.filters.all_filters

   [pci]
   passthrough_whitelist = [{"vendor_id": "8086", "product_id": "10fb"}]
   alias = [{"vendor_id":"8086", "product_id":"10ed", "device_type":"type-VF", "name":"vf1"}]

.. end

Run deployment.

Verification
------------

Create (or use an existing) flavor, and then configure it to request one PCI
device from the PCI alias:

.. code-block:: console

   # openstack flavor set sriov-flavor --property "pci_passthrough:alias"="vf1:1"

.. end

Start a new instance using the flavor:

.. code-block:: console

   # openstack server create --flavor sriov-flavor --image fc-26 vm2

.. end

Verify VF devices were created and the instance starts successfully as in
the Neutron SRIOV case.

For more information see `OpenStack PCI passthrough documentation <https://docs.openstack.org/nova/rocky/admin/pci-passthrough.html>`_.
