.. _designate-guide:

==================
Designate in Kolla
==================

Overview
~~~~~~~~

Designate provides DNSaaS services for OpenStack:

-  REST API for domain/record management
-  Multi-tenant
-  Integrated with Keystone for authentication
-  Framework in place to integrate with Nova and Neutron
   notifications (for auto-generated records)
-  Support for PowerDNS and Bind9 out of the box

Configuration on Kolla deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable Designate service in ``/etc/kolla/globals.yml``

.. code-block:: yaml

   enable_designate: "yes"

.. end

Configure Designate options in ``/etc/kolla/globals.yml``

.. important::

   Designate MDNS node requires the ``dns_interface`` to be reachable from
   public network.

.. code-block:: yaml

   dns_interface: "eth1"
   designate_backend: "bind9"
   designate_ns_record: "sample.openstack.org"

.. end

Neutron and Nova Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create default Designate Zone for Neutron:

.. code-block:: console

   openstack zone create --email admin@sample.openstack.org sample.openstack.org.

.. end

Create designate-sink custom configuration folder:

.. code-block:: console

   mkdir -p /etc/kolla/config/designate/

.. end

Append Designate Zone ID in ``/etc/kolla/config/designate/designate-sink.conf``

.. code-block:: console

   [handler:nova_fixed]
   zone_id = <ZONE_ID>
   [handler:neutron_floatingip]
   zone_id = <ZONE_ID>

.. end

Reconfigure Designate:

.. code-block:: console

   kolla-ansible reconfigure -i <INVENTORY_FILE> --tags designate

.. end

Verify operation
~~~~~~~~~~~~~~~~

List available networks:

.. code-block:: console

   openstack network list

.. end

Associate a domain to a network:

.. code-block:: console

   neutron net-update <NETWORK_ID> --dns_domain sample.openstack.org.

.. end

Start an instance:

.. code-block:: console

   openstack server create \
     --image cirros \
     --flavor m1.tiny \
     --key-name mykey \
     --nic net-id=${NETWORK_ID} \
     my-vm

.. end

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

.. end

Query instance DNS information to Designate ``dns_interface`` IP address:

.. code-block:: console

   dig +short -p 5354 @<DNS_INTERFACE_IP> my-vm.sample.openstack.org. A
   192.168.190.232

.. end

For more information about how Designate works, see
`Designate, a DNSaaS component for OpenStack
<https://docs.openstack.org/designate/latest/>`__.
