.. _designate-guide:

==================
Designate in Kolla
==================

Overview
========
Designate provides DNSaaS services for OpenStack:

  -  REST API for domain/record management
  -  Multi-tenant
  -  Integrated with Keystone for authentication
  -  Framework in place to integrate with Nova and Neutron
     notifications (for auto-generated records)
  -  Support for PowerDNS and Bind9 out of the box

Configuration on Kolla deployment
---------------------------------

Enable Designate service in ``/etc/kolla/globals.yml``

.. code-block:: console

    enable_designate: "yes"

Configure Designate options in ``/etc/kolla/globals.yml``

.. important::

    Designate MDNS node requires the ``dns_interface`` to be reachable from
    public network.

.. code-block:: console

    dns_interface: "eth1"
    designate_backend: "bind9"
    designate_ns_record: "sample.openstack.org"

Neutron and Nova Integration
----------------------------

Create default Designate Zone for Neutron:

.. code-block:: console

    $ openstack zone create --email admin@sample.openstack.org sample.openstack.org.

Create designate-sink custom configuration folder:

.. code-block:: console

   $ mkdir -p /etc/kolla/config/designate/designate-sink/

Append Designate Zone ID in ``/etc/kolla/config/designate/designate-sink.conf``

.. code-block:: console

    [handler:nova_fixed]
    zone_id = <ZONE_ID>
    [handler:neutron_floatingip]
    zone_id = <ZONE_ID>

Reconfigure Designate:

.. code-block:: console

    $ kolla-ansible reconfigure -i <INVENTORY_FILE> --tags designate

Verify operation
----------------

List available networks:

.. code-block:: console

    $ neutron net-list

Associate a domain to a network:

.. code-block:: console

    $ neutron net-update <NETWORK_ID> --dns_domain sample.openstack.org.

Start an instance:

.. code-block:: console

    $ openstack server create \
      --image cirros \
      --flavor m1.tiny \
      --key-name mykey \
      --nic net-id=${NETWORK_ID} \
      my-vm

Check DNS records in Designate:

.. code-block:: console

    $ designate record-list sample.openstack.org.
    +--------------------------------------+------+---------------------------------------+---------------------------------------------+
    | id                                   | type | name                                  | data                                        |
    +--------------------------------------+------+---------------------------------------+---------------------------------------------+
    | 5aec6f5b-2121-4a2e-90d7-9e4509f79506 | SOA  | sample.openstack.org.                 | sample.openstack.org.                       |
    |                                      |      |                                       | admin.sample.openstack.org. 1485266928 3514 |
    |                                      |      |                                       | 600 86400 3600                              |
    | 578dc94a-df74-4086-a352-a3b2db9233ae | NS   | sample.openstack.org.                 | sample.openstack.org.                       |
    | de9ff01e-e9ef-4a0f-88ed-6ec5ecabd315 | A    | 192-168-190-232.sample.openstack.org. | 192.168.190.232                             |
    | f67645ee-829c-4154-a988-75341050a8d6 | A    | my-vm.None.sample.openstack.org.      | 192.168.190.232                             |
    | e5623d73-4f9f-4b54-9045-b148e0c3342d | A    | my-vm.sample.openstack.org.           | 192.168.190.232                             |
    +--------------------------------------+------+---------------------------------------+---------------------------------------------+

Query instance DNS information to Designate ``dns_interface`` IP address:

.. code-block:: console

    $ dig +short -p 5354 @<DNS_INTERFACE_IP> my-vm.sample.openstack.org. A
    192.168.190.232

For more information about how Designate works, see
`Designate, a DNSaaS component for OpenStack
<http://docs.openstack.org/developer/designate>`__.
