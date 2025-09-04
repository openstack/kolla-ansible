.. _designate-guide:

=======================
Designate - DNS service
=======================

Overview
~~~~~~~~

Designate provides DNSaaS services for OpenStack:

*  REST API for domain/record management
*  Multi-tenant
*  Integrated with Keystone for authentication
*  Framework in place to integrate with Nova and Neutron
   notifications (for auto-generated records)
*  Support for Bind9 and Infoblox out of the box

Configuration on Kolla deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable Designate service in ``/etc/kolla/globals.yml``

.. code-block:: yaml

   enable_designate: "yes"
   neutron_dns_domain: "example.org."

.. important::
   The ``neutron_dns_domain`` value has to be different to ``openstacklocal``
   (its default value) and has to end with a period ``.``.

.. important::
   ``DNS Integration`` is enabled by default and can be disabled by
   adding ``neutron_dns_integration: no`` to ``/etc/kolla/globals.yml``
   and reconfiguring with ``--tags`` neutron.

Configure Designate options in ``/etc/kolla/globals.yml``

.. important::

   Designate MDNS node requires the ``dns_interface`` to be reachable from
   management network.

.. code-block:: yaml

   dns_interface: "eth1"
   designate_ns_record:
     - "ns1.sample.openstack.org"

.. important::

   If multiple nodes are assigned to be Designate workers, then you must
   enable a supported coordination backend, currently only ``valkey``
   is supported. The backend choice can be overridden via the
   ``designate_coordination_backend`` variable. It defaults to ``valkey``
   when ``valkey`` is enabled (``enable_valkey`` is set to ``yes``).

The following additional variables are required depending on which backend you
intend to use:

Bind9 Backend
-------------

Configure Designate options in ``/etc/kolla/globals.yml``

.. code-block:: yaml

   designate_backend: "bind9"

Infoblox Backend
----------------

.. important::

   When using Infoblox as the Designate backend the MDNS node
   requires the container to listen on port 53. As this is a privileged
   port you will need to build your designate-mdns container to run
   as the user root rather than designate.

Configure Designate options in ``/etc/kolla/globals.yml``

.. code-block:: yaml

   designate_backend: "infoblox"
   designate_backend_infoblox_nameservers: "192.168.1.1,192.168.1.2"
   designate_infoblox_host: "192.168.1.1"
   designate_infoblox_wapi_url: "https://infoblox.example.com/wapi/v2.1/"
   designate_infoblox_auth_username: "username"
   designate_infoblox_ns_group: "INFOBLOX"

Configure Designate options in ``/etc/kolla/passwords.yml``

.. code-block:: yaml

    designate_infoblox_auth_password: "password"

For more information about how the Infoblox backend works, see
:designate-doc:`Infoblox backend <admin/backends/infoblox.html>`.

Neutron and Nova Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``designate-sink`` is an optional service which listens for event
notifications, such as compute.instance.create.end, handlers are
available for Nova and Neutron. Notification events can then be used
to trigger record creation & deletion.

.. note::
   Service ``designate-sink`` in kolla deployments is disabled by default
   and can be enabled by ``designate_enable_notifications_sink: yes``.

Create default Designate Zone for Neutron:

.. code-block:: console

   openstack zone create --email admin@sample.openstack.org sample.openstack.org.

Create designate-sink custom configuration folder:

.. code-block:: console

   mkdir -p /etc/kolla/config/designate/

Append Designate Zone ID in ``/etc/kolla/config/designate/designate-sink.conf``

.. code-block:: console

   [handler:nova_fixed]
   zone_id = <ZONE_ID>
   [handler:neutron_floatingip]
   zone_id = <ZONE_ID>

Reconfigure Designate:

.. code-block:: console

   kolla-ansible reconfigure -i <INVENTORY_FILE> --tags designate,neutron,nova

Verify operation
~~~~~~~~~~~~~~~~

List available networks:

.. code-block:: console

   openstack network list

Associate a domain to a network:

.. code-block:: console

   openstack network set <NETWORK_ID> --dns-domain sample.openstack.org.

Start an instance:

.. code-block:: console

   openstack server create \
     --image cirros \
     --flavor m1.tiny \
     --key-name mykey \
     --nic net-id=${NETWORK_ID} \
     my-vm

Check DNS records in Designate:

.. code-block:: console

   openstack recordset list sample.openstack.org.

   +--------------------------------------+---------------------------------------+------+---------------------------------------------+--------+--------+
   | id                                   | name                                  | type | records                                     | status | action |
   +--------------------------------------+---------------------------------------+------+---------------------------------------------+--------+--------+
   | 5aec6f5b-2121-4a2e-90d7-9e4509f79506 | sample.openstack.org.                 | SOA  | sample.openstack.org.                       | ACTIVE | NONE   |
   |                                      |                                       |      | admin.sample.openstack.org. 1485266928 3514 |        |        |
   |                                      |                                       |      | 600 86400 3600                              |        |        |
   | 578dc94a-df74-4086-a352-a3b2db9233ae | sample.openstack.org.                 | NS   | sample.openstack.org.                       | ACTIVE | NONE   |
   | de9ff01e-e9ef-4a0f-88ed-6ec5ecabd315 | 192-168-190-232.sample.openstack.org. | A    | 192.168.190.232                             | ACTIVE | NONE   |
   | f67645ee-829c-4154-a988-75341050a8d6 | my-vm.None.sample.openstack.org.      | A    | 192.168.190.232                             | ACTIVE | NONE   |
   | e5623d73-4f9f-4b54-9045-b148e0c3342d | my-vm.sample.openstack.org.           | A    | 192.168.190.232                             | ACTIVE | NONE   |
   +--------------------------------------+---------------------------------------+------+---------------------------------------------+--------+--------+

Query instance DNS information to Designate ``dns_interface`` IP address:

.. code-block:: console

   dig +short -p 5354 @<DNS_INTERFACE_IP> my-vm.sample.openstack.org. A
   192.168.190.232

For more information about how Designate works, see
`Designate, a DNSaaS component for OpenStack
<https://docs.openstack.org/designate/latest/>`__.
