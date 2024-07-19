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

.. warning::

   OVN VPNaaS is currently not supported on RHEL 10 based distributions
   (e.g., Rocky Linux 10, CentOS Stream 10) due to an upstream bug in
   Neutron. See `LP#2146308 <https://bugs.launchpad.net/neutron/+bug/2146308>`_
   for details.

Preparation and deployment
--------------------------

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_neutron_vpnaas: "yes"

Verification
------------

VPNaaS is a complex subject, hence this document provides directions for a
simple smoke test to verify the service is up and running.

In ml2/ovn setups a special neutron_ovn_vpn_agent is running on neutron
node(s).
Version may differ depending on deploy configuration:

.. code-block:: console

   # docker ps --filter name=neutron_ovn_vpn_agent

    CONTAINER ID   IMAGE                                COMMAND                  CREATED      STATUS                PORTS     NAMES
    7f6efad28d30   kolla/neutron-ovn-vpn-agent:18.1.0   "dumb-init --single-…"   7 days ago   Up 7 days (healthy)             neutron_ovn_vpn_agent

On ml2/ovs deployments there is no special agent.
The vpnaas code is running inside the neutron_l3_agent container.


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

   # openstack vpn service list

    +--------------------------------------+----------+--------------------------------------+--------+--------+-------+--------+
    | ID                                   | Name     | Router                               | Subnet | Flavor | State | Status |
    +--------------------------------------+----------+--------------------------------------+--------+--------+-------+--------+
    | 03f85023-28d9-4f35-a10e-2c8dd3c11b65 | vpn_west | e3603217-fd22-404c-b27e-9285c2a79a17 | None   | None   | True  | ACTIVE |
    | 1abdc71a-2eb7-4b2a-8871-eb9d91f39957 | vpn_east | 3485bdd2-4c42-449e-ae9f-d071a8cb9e5c | None   | None   | True  | ACTIVE |
    +--------------------------------------+----------+--------------------------------------+--------+--------+-------+--------+

Two VMs can now be booted, one on vpn_east, the other on vpn_west, and
encrypted ping packets observed being sent from one to the other.

For more information on VPNaaS in Neutron refer to the
`OpenStack docs <https://docs.openstack.org/neutron-vpnaas>`_.

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
