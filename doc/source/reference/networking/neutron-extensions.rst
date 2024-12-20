.. _neutron-extensions:

==================
Neutron Extensions
==================

Networking-SFC
~~~~~~~~~~~~~~

Preparation and deployment
--------------------------

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_neutron_sfc: "yes"

Verification
------------

For setting up a testbed environment and creating a port chain, please refer
to :networking-sfc-doc:`networking-sfc documentation
<contributor/system_design_and_workflow.html>`.

Neutron FWaaS (Firewall-as-a-Service)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Preparation and deployment
--------------------------

.. warning::

   FWaaS has currently no support for OVN.

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_neutron_fwaas: "yes"

For more information on FWaaS in Neutron refer to the
:neutron-doc:`Neutron FWaaS docs <admin/fwaas.html>`.

Neutron VPNaaS (VPN-as-a-Service)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Preparation and deployment
--------------------------

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_neutron_vpnaas: "yes"

Verification
------------

VPNaaS is a complex subject, hence this document provides directions for a
simple smoke test to verify the service is up and running.

On the network node(s), the ``neutron_vpnaas_agent`` should be up (image naming
and versioning may differ depending on deploy configuration):

.. code-block:: console

   # docker ps --filter name=neutron_vpnaas_agent

   CONTAINER ID   IMAGE                                                               COMMAND         CREATED          STATUS        PORTS  NAMES
   97d25657d55e   operator:5000/kolla/centos-source-neutron-vpnaas-agent:4.0.0   "kolla_start"   44 minutes ago   Up 44 minutes        neutron_vpnaas_agent

.. warning::

   You are free to use the following ``init-runonce`` script for demo
   purposes but note it does **not** have to be run in order to use your
   cloud. Depending on your customisations, it may not work, or it may
   conflict with the resources you want to create. You have been warned.

   Similarly, the ``init-vpn`` script does **not** have to be run unless
   you want to follow this particular demo.

Kolla Ansible includes a small script that can be used in tandem with
``tools/init-runonce`` to verify the VPN using two routers and two Nova VMs:

.. code-block:: console

   tools/init-runonce
   tools/init-vpn

Verify both VPN services are active:

.. code-block:: console

   # neutron vpn-service-list

   +--------------------------------------+----------+--------------------------------------+--------+
   | id                                   | name     | router_id                            | status |
   +--------------------------------------+----------+--------------------------------------+--------+
   | ad941ec4-5f3d-4a30-aae2-1ab3f4347eb1 | vpn_west | 051f7ce3-4301-43cc-bfbd-7ffd59af539e | ACTIVE |
   | edce15db-696f-46d8-9bad-03d087f1f682 | vpn_east | 058842e0-1d01-4230-af8d-0ba6d0da8b1f | ACTIVE |
   +--------------------------------------+----------+--------------------------------------+--------+

Two VMs can now be booted, one on vpn_east, the other on vpn_west, and
encrypted ping packets observed being sent from one to the other.

For more information on this and VPNaaS in Neutron refer to the
:neutron-vpnaas-doc:`Neutron VPNaaS Testing <contributor/index.html#testing>`
and the `OpenStack wiki <https://wiki.openstack.org/wiki/Neutron/VPNaaS>`_.

Trunking
~~~~~~~~

The network trunk service allows multiple networks to be connected to an
instance using a single virtual NIC (vNIC). Multiple networks can be presented
to an instance by connecting it to a single port.

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_neutron_trunk: "yes"

Neutron Logging Framework
~~~~~~~~~~~~~~~~~~~~~~~~~

Preparation and deployment
--------------------------

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_neutron_packet_logging: "yes"

For OVS deployment, you need to override the firewall driver in
`openvswitch_agent.ini` to:

.. code-block:: ini

   [security_group]
   firewall_driver = openvswitch

Verification
------------

Verify that loggable resources are properly registered:

.. code-block:: console

   # openstack network loggable resources list
   +-----------------+
   | Supported types |
   +-----------------+
   | security_group  |
   +-----------------+

The output shows security groups logging is now enabled.

You may now create a network logging rule to log all events based on a
security group object:

.. code-block:: console

   # openstack network log create --resource-type security_group \
   --description "Collecting all security events" \
   --event ALL Log_Created

More examples and information can be found at:
https://docs.openstack.org/neutron/latest/admin/config-logging.html
