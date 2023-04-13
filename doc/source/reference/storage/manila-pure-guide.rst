.. _manila-pure-guide:

==========================================================
Pure Storage FlashBlade File Services Driver for OpenStack
==========================================================

Overview
~~~~~~~~
The Pure Storage FlashBlade File Services Driver for OpenStack
provides NFS Shared File Systems to OpenStack.


Requirements
------------
- Pure Storage FlashBlade

- Purity//FB v2.3.0 or higher


Supported shared file systems and operations
--------------------------------------------
The driver supports NFS shares.

The following operations are supported:

- Create a share.

- Delete a share.

- Allow share access.

- Deny share access.

- Create a snapshot.

- Delete a snapshot.

- Revert from snapshot.

- Extend a share.

- Shrink a share.


Preparation and Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. important ::

   It is mandatory that FlashBlade management interface is reachable from the
   Shared File System node through the admin network, while the selected
   EVS data interface is reachable from OpenStack Cloud, such as through
   Neutron flat networking.


Configuration on Kolla deployment
---------------------------------

Enable Shared File Systems service and FlashBlade driver in
``/etc/kolla/globals.yml``

.. code-block:: yaml

   enable_manila: "yes"
   enable_manila_backend_flashblade: "yes"

Configure the OpenStack networking so it can reach FlashBlade Management
interface and FlashBlade Data interface.

To configure two physical networks, physnet1 and physnet2, with
ports eth1 and eth2 associated respectively:

In ``/etc/kolla/globals.yml`` set:

.. code-block:: yaml

   neutron_bridge_name: "br-ex,br-ex2"
   neutron_external_interface: "eth1,eth2"

.. note::

   ``eth1`` is used to Neutron external interface and ``eth2`` is
   used to FlashBlade data interface.

FlashBlade back end configuration
---------------------------------

In ``/etc/kolla/globals.yml`` uncomment and set:

.. code-block:: yaml

   manila_flashblade_mgmt_vip: "172.24.44.15"
   manila_flashblade_data_vip: "172.24.45.22"
   manila_flashblade_api: "<API token for admin-privilaged user>"

Configuration on FlashBlade
---------------------------

Create the FlashBlade data network in Kolla OpenStack:

List the available tenants:

.. code-block:: console

   $ openstack project list

Create a network to the given tenant (service), providing the tenant ID,
a name for the network, the name of the physical network over which the
virtual network is implemented, and the type of the physical mechanism by
which the virtual network is implemented:

.. code-block:: console

   $ openstack network create --project <SERVICE_ID> \
     --provider-physical-network physnet2 \
     --provider-network-type flat \
     flashblade_network

*Optional* - List available networks:

.. code-block:: console

   $ openstack network list

Create a subnet to the same tenant (service), the gateway IP of this subnet,
a name for the subnet, the network ID created before, and the CIDR of
subnet:

.. code-block:: console

   $ openstack subnet create --project <SERVICE_ID>  --gateway <GATEWAY> \
     --subnet_range <SUBNET_CIDR> flashblade_subnet

*Optional* - List available subnets:

.. code-block:: console

   $ openstack subnet list

Add the subnet interface to a router, providing the router ID and subnet
ID created before:

.. code-block:: console

   $ openstack router add submet <ROUTER_ID> <SUBNET_ID>

Create a share
~~~~~~~~~~~~~~

Create a default share type before running manila-share service:

.. code-block:: console

   $ openstack share type create default_share_flashblade False

   +--------------------------------------+--------------------------+------------+------------+--------------------------------------+-------------------------+
   | ID                                   | Name                     | visibility | is_default | required_extra_specs                 | optional_extra_specs    |
   +--------------------------------------+--------------------------+------------+------------+--------------------------------------+-------------------------+
   | 3e54c8a2-1e50-455e-89a0-96bb52876c35 | default_share_flashblade | public     | -          | driver_handles_share_servers : False | snapshot_support : True |
   +--------------------------------------+--------------------------+------------+------------+--------------------------------------+-------------------------+

Create a NFS share using the FlashBlade back end:

.. code-block:: console

   $ openstack share create --name <myflashbladeshare \
     --description "My Manila share" \
     --share-type default_share_flashblade \
     NFS 1

Verify Operation:

.. code-block:: console

   $ openstack share list

   +--------------------------------------+-------------------+------+-------------+-----------+-----------+--------------------------+-----------------+-------------------+
   | ID                                   | Name              | Size | Share Proto | Status    | Is Public | Share Type Name          | Host            | Availability Zone |
   +--------------------------------------+-------------------+------+-------------+-----------+-----------+--------------------------+-----------------+-------------------+
   | 721c0a6d-eea6-41af-8c10-72cd98985203 | myflashbladeshare | 1    | NFS         | available | False     | default_share_flashblade | control@fb1#FB1 | nova              |
   +--------------------------------------+-------------------+------+-------------+-----------+-----------+--------------------------+-----------------+-------------------+

.. code-block:: console

   $ openstack share show myflashbladeshare

   +-----------------------------+-----------------------------------------------------------------+
   | Property                    | Value                                                           |
   +-----------------------------+-----------------------------------------------------------------+
   | status                      | available                                                       |
   | share_type_name             | default_share_flashblade                                        |
   | description                 | My Manila share                                                 |
   | availability_zone           | nova                                                            |
   | share_network_id            | None                                                            |
   | export_locations            |                                                                 |
   |                             | path = 172.24.53.1:/shares/45ed6670-688b-4cf0-bfe7-34956648fb84 |
   |                             | preferred = False                                               |
   |                             | is_admin_only = False                                           |
   |                             | id = e81e716f-f1bd-47b2-8a56-2c2f9e33a98e                       |
   |                             | share_instance_id = 45ed6670-688b-4cf0-bfe7-34956648fb84        |
   | share_server_id             | None                                                            |
   | host                        | control@fb1#FB1                                                 |
   | access_rules_status         | active                                                          |
   | snapshot_id                 | None                                                            |
   | is_public                   | False                                                           |
   | task_state                  | None                                                            |
   | snapshot_support            | True                                                            |
   | id                          | 721c0a6d-eea6-41af-8c10-72cd98985203                            |
   | size                        | 1                                                               |
   | user_id                     | ba7f6d543713488786b4b8cb093e7873                                |
   | name                        | myflashbladeshare                                               |
   | share_type                  | 3e54c8a2-1e50-455e-89a0-96bb52876c35                            |
   | has_replicas                | False                                                           |
   | replication_type            | None                                                            |
   | created_at                  | 2016-10-14T14:50:47.000000                                      |
   | share_proto                 | NFS                                                             |
   | consistency_group_id        | None                                                            |
   | source_cgsnapshot_member_id | None                                                            |
   | project_id                  | c3810d8bcc3346d0bdc8100b09abbbf1                                |
   | metadata                    | {}                                                              |
   +-----------------------------+-----------------------------------------------------------------+

.. _flashblade_configure_multiple_back_ends:

Configure multiple back ends
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An administrator can configure an instance of Manila to provision shares from
one or more back ends. Each back end leverages an instance of a vendor-specific
implementation of the Manila driver API.

The name of the back end is declared as a configuration option
share_backend_name within a particular configuration stanza that contains the
related configuration options for that back end.

So, in the case of an multiple back ends deployment, it is necessary to change
the default share backends before deployment.

Modify the file ``/etc/kolla/config/manila.conf`` and add the contents:

.. path /etc/kolla/config/manila.conf
.. code-block:: ini

   [DEFAULT]
   enabled_share_backends = generic,fb1,fb2

Modify the file ``/etc/kolla/config/manila-share.conf`` and add the contents:

.. path /etc/kolla/config/manila-share.conf
.. code-block:: ini

   [generic]
   share_driver = manila.share.drivers.generic.GenericShareDriver
   interface_driver = manila.network.linux.interface.OVSInterfaceDriver
   driver_handles_share_servers = True
   service_instance_password = manila
   service_instance_user = manila
   service_image_name = manila-service-image
   share_backend_name = GENERIC

   [fb1]
   share_backend_name = FB1
   share_driver = manila.share.drivers.purestorage.flashblade.FlashBladeShareDriver
   driver_handles_share_servers = False
   flashblade_mgmt_vip = <fb1_mgmt_ip>
   flashblade_data_vip = <fb1_data_ip>
   flashblade_api = <FB1 API token>

   [fb2]
   share_backend_name = FB2
   share_driver = manila.share.drivers.purestorage.flashblade.FlashBladeShareDriver
   driver_handles_share_servers = False
   flashblade_mgmt_vip = <fb2_mgmt_ip>
   flashblade_data_vip = <fb2_data_ip>
   flashblade_api = <FB2 API token>

For more information about how to manage shares, see the
:manila-doc:`Manage shares <user/create-and-manage-shares.html>`.

For details on how to use the Pure Storage FlashBlade, refer to the
`Pure Storage Manila Reference Guide <https://docs.openstack.org/manila/latest/configuration/shared-file-systems/drivers/purestorage-flashblade-driver.html>`_.

The use of this backend requires that the ``purity_fb`` SDK package is
installed in the ``manila-share`` container. To do this follow the steps
outlined in the `kolla image building guide <https://docs.openstack.org/kolla/latest/admin/image-building.html>`_
particularly the ``Package Customisation`` and ``Custom Repos`` sections.
