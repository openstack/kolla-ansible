.. _dpdk:

====
DPDK
====

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

As dpdk is a userspace networking library it requires userspace compatible
drivers to be able to control the physical interfaces on the platform.
dpdk technically support 3 kernel drivers ``igb_uio``, ``uio_pci_generic`` and
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

.. note::

   Kolla doesn't support ovs-dpdk for RHEL-based distros due to the lack
   of a suitable package.

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
