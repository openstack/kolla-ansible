.. _sriov:

=====
SRIOV
=====

Neutron SRIOV
~~~~~~~~~~~~~

Preparation and deployment
--------------------------

SRIOV requires specific NIC and BIOS configuration and is not supported on all
platforms. Consult NIC and platform specific documentation for instructions
on enablement.

Modify the ``/etc/kolla/globals.yml`` file as the following example
shows which automatically appends ``sriovnicswitch`` to the
``mechanism_drivers`` inside ``ml2_conf.ini``.

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   enable_neutron_sriov: "yes"

It is also a requirement to define physnet:interface mappings for all
SRIOV devices as shown in the following example where ``sriovtenant1`` is the
physnet mapped to ``ens785f0`` interface:

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   neutron_sriov_physnet_mappings:
     sriovtenant1: ens785f0

However, the provider networks using SRIOV should be configured.
Both flat and VLAN are configured with the same physical network name
in this example:

.. path /etc/kolla/config/neutron/ml2_conf.ini
.. code-block:: ini

   [ml2_type_vlan]
   network_vlan_ranges = sriovtenant1:1000:1009

   [ml2_type_flat]
   flat_networks = sriovtenant1

Modify the ``nova.conf`` file and add ``PciPassthroughFilter`` to
``enabled_filters``. This filter is required by the Nova Scheduler
service on the controller node.

.. path /etc/kolla/config/nova.conf
.. code-block:: ini

   [filter_scheduler]
   enabled_filters = <existing filters>, PciPassthroughFilter
   available_filters = nova.scheduler.filters.all_filters

PCI devices listed under ``neutron_sriov_physnet_mappings`` will be
whitelisted on the Compute hosts inside ``nova.conf``.

Physical network to interface mappings in ``neutron_sriov_physnet_mappings``
will be automatically added to ``sriov_agent.ini``. Specific VFs can be
excluded via ``excluded_devices``. However, leaving blank (default) leaves all
VFs enabled:

.. path /etc/kolla/config/neutron/sriov_agent.ini
.. code-block:: ini

   [sriov_nic]
   exclude_devices =

To use OpenvSwitch hardware offloading modify `/etc/kolla/globals.yml``:

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   openvswitch_hw_offload: "yes"

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

Verify the SRIOV Agent container is running on the compute node(s):

.. code-block:: console

   # docker ps --filter name=neutron_sriov_agent
   CONTAINER ID   IMAGE                                                                COMMAND        CREATED         STATUS         PORTS  NAMES
   b03a8f4c0b80   10.10.10.10:4000/registry/centos-source-neutron-sriov-agent:17.04.0  "kolla_start"  18 minutes ago  Up 18 minutes         neutron_sriov_agent

Verify the SRIOV Agent service is present and UP:

.. code-block:: console

   # openstack network agent list

   +--------------------------------------+--------------------+-------------+-------------------+-------+-------+---------------------------+
   | ID                                   | Agent Type         | Host        | Availability Zone | Alive | State | Binary                    |
   +--------------------------------------+--------------------+-------------+-------------------+-------+-------+---------------------------+
   | 7c06bda9-7b87-487e-a645-cc6c289d9082 | NIC Switch agent   | av09-18-wcp | None              | :-)   | UP    | neutron-sriov-nic-agent   |
   +--------------------------------------+--------------------+-------------+-------------------+-------+-------+---------------------------+

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

Create a port on the provider network with ``vnic_type`` set to ``direct``:

.. code-block:: console

   # openstack port create --network sriovnet1 --vnic-type=direct sriovnet1-port1

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

For more information see :neutron-doc:`OpenStack SRIOV documentation
<admin/config-sriov.html>`.

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

   [filter_scheduler]
   enabled_filters = <existing filters>, PciPassthroughFilter
   available_filters = nova.scheduler.filters.all_filters

   [pci]
   device_spec = [{"vendor_id": "8086", "product_id": "10fb"}]
   alias = {"vendor_id":"8086", "product_id":"10ed", "device_type":"type-VF", "name":"vf1"}

Run deployment.

Verification
------------

Create (or use an existing) flavor, and then configure it to request one PCI
device from the PCI alias:

.. code-block:: console

   # openstack flavor set sriov-flavor --property "pci_passthrough:alias"="vf1:1"

Start a new instance using the flavor:

.. code-block:: console

   # openstack server create --flavor sriov-flavor --image fc-26 vm2

Verify VF devices were created and the instance starts successfully as in
the Neutron SRIOV case.

For more information see :nova-doc:`OpenStack PCI passthrough documentation
<admin/pci-passthrough.html>`.
