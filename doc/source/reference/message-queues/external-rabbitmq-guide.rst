.. _external-rabbitmq-guide:

=================
External RabbitMQ
=================

Sometimes, for various reasons (Redundancy, organisational policies, etc.),
it might be necessary to use an external RabbitMQ cluster.
This use case can be achieved with the following steps:

Requirements
~~~~~~~~~~~~

* An existing RabbitMQ cluster, reachable from all of your
  nodes.

Enabling External RabbitMQ support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to enable external RabbitMQ support,
you will first need to disable RabbitMQ deployment,
by ensuring the following line exists within ``/etc/kolla/globals.yml`` :

.. code-block:: yaml

   enable_rabbitmq: "no"


Overwriting transport_url within ``globals.yml``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you use an external RabbitMQ cluster, you must overwrite
``*_transport_url`` within ``/etc/kolla/globals.yml``

.. code-block:: yaml

   rpc_transport_url:
   notify_transport_url:
   nova_cell_rpc_transport_url:
   nova_cell_notify_transport_url:

For example:

.. code-block:: yaml

   rpc_transport_url: rabbit://openstack:6Y6Eh3blPXB1Qn4190JKxRoyVhTaFsY2k2V0DuIc@10.0.0.1:5672,openstack:6Y6Eh3blPXB1Qn4190JKxRoyVhTaFsY2k2V0DuIc@10.0.0.2:5672,openstack:6Y6Eh3blPXB1Qn4190JKxRoyVhTaFsY2k2V0DuIc@10.0.0.3:5672//
   notify_transport_url: "{{ rpc_transport_url }}"
   nova_cell_rpc_transport_url: rabbit://openstack:6Y6Eh3blPXB1Qn4190JKxRoyVhTaFsY2k2V0DuIc@10.0.0.1:5672//
   nova_cell_notify_transport_url: "{{ nova_cell_rpc_transport_url }}"

.. note::

   Ensure the rabbitmq user used in ``*_transport_url`` exists.
