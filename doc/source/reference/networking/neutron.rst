.. _neutron:

============================
Neutron - Networking Service
============================

Preparation and deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~

Neutron is enabled by default in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   #enable_neutron: "{{ enable_openstack_core | bool }}"

Neutron external interface is used for communication with the external world,
for example provider networks and floating IPs.
For setting up the neutron external interface please modify
``/etc/kolla/globals.yml`` setting ``neutron_external_interface`` to the
desired interface name, ``eth1`` in the example below:

.. code-block:: yaml

   neutron_external_interface: "eth1"

.. note::
   This is used by hosts in the ``network`` group, and hosts in the ``compute``
   group if ``enable_neutron_provider_networks`` is set or DVR is enabled.

To use provider networks in instances you also need to set the following in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_neutron_provider_networks: yes

.. note::
   ``enable_neutron_provider_networks`` ensures ``neutron_external_interface``
   is used on hosts in the ``compute`` group.

OpenvSwitch (ml2/ovs)
~~~~~~~~~~~~~~~~~~~~~

By default ``kolla-ansible`` uses ``openvswitch`` as its underlying network
mechanism, you can change that using the ``neutron_plugin_agent`` variable in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   neutron_plugin_agent: "openvswitch"

When using Open vSwitch on a compatible kernel (4.3+ upstream, consult the
documentation of your distribution for support details), you can switch
to using the native OVS firewall driver by employing a configuration override
(see :ref:`service-config`). You can set it in
``/etc/kolla/config/neutron/openvswitch_agent.ini``:

.. code-block:: ini

   [security_group]
   firewall_driver = openvswitch

OVN (ml2/ovn)
~~~~~~~~~~~~~

In order to use ``OVN`` as mechanism driver for ``neutron``, you need to set
the following:

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   neutron_plugin_agent: "ovn"

When using OVN - Kolla-Ansible will not enable distributed floating ip
functionality (not enable external bridges on computes) by default.
To change this behaviour you need to set the following:

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   neutron_ovn_distributed_fip: "yes"

