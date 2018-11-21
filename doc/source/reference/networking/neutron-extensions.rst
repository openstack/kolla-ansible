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
to `networking-sfc documentation
<https://docs.openstack.org/networking-sfc/latest/contributor/system_design_and_workflow.html>`__.

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
   97d25657d55e   operator:5000/kolla/oraclelinux-source-neutron-vpnaas-agent:4.0.0   "kolla_start"   44 minutes ago   Up 44 minutes        neutron_vpnaas_agent

Kolla-Ansible includes a small script that can be used in tandem with
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
`Neutron VPNaaS Testing <https://docs.openstack.org/neutron-vpnaas/latest/contributor/index.html#testing>`__
and the `OpenStack wiki <https://wiki.openstack.org/wiki/Neutron/VPNaaS>`_.
