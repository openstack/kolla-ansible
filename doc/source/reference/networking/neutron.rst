.. _neutron:

============================
Neutron - Networking Service
============================

Preparation and deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~

Neutron is enabled by default in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   #enable_neutron: "{{ enable_openstack_core | bool }}"

Network interfaces
~~~~~~~~~~~~~~~~~~

Neutron external interface is used for communication with the external world,
for example provider networks, routers and floating IPs.
For setting up the neutron external interface modify
``/etc/kolla/globals.yml`` setting ``neutron_external_interface`` to the
desired interface name. This interface is used by hosts in the ``network``
group. It is also used by hosts in the ``compute`` group if
``enable_neutron_provider_networks`` is set or DVR is enabled.

The interface is plugged into a bridge (Open vSwitch or Linux Bridge, depending
on the driver) defined by ``neutron_bridge_name``, which defaults to ``br-ex``.
The default Neutron physical network is ``physnet1``.

Example: single interface
-------------------------

In the case where we have only a single Neutron external interface,
configuration is simple:

.. code-block:: yaml

   neutron_external_interface: "eth1"

Example: multiple interfaces
----------------------------

In some cases it may be necessary to have multiple external network interfaces.
This may be achieved via comma-separated lists:

.. code-block:: yaml

   neutron_external_interface: "eth1,eth2"
   neutron_bridge_name: "br-ex1,br-ex2"

These two lists are "zipped" together, such that ``eth1`` is plugged into the
``br-ex1`` bridge, and ``eth2`` is plugged into the ``br-ex2`` bridge.  Kolla
Ansible maps these interfaces to Neutron physical networks ``physnet1`` and
``physnet2`` respectively.

Example: shared interface
-------------------------

Sometimes an interface used for Neutron external networking may also be used
for other traffic. Plugging an interface directly into a bridge would prevent
us from having a usable IP address on the interface. One solution to this issue
is to use an intermediate Linux bridge and virtual Ethernet pair, then assign
IP addresses on the Linux bridge. This setup is supported by
:kayobe-doc:`Kayobe </>`. It is out of scope here, as it is non-trivial to set
up in a persistent manner.

Provider networks
~~~~~~~~~~~~~~~~~

Provider networks allow to connect compute instances directly to physical
networks avoiding tunnels. This is necessary for example for some performance
critical applications. Only administrators of OpenStack can create such
networks.

To use provider networks in instances you also need to set the following in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_neutron_provider_networks: yes

For provider networks, compute hosts must have an external bridge
created and configured by Ansible (this is also necessary when
:neutron-doc:`Neutron Distributed Virtual Routing (DVR)
<admin/deploy-ovs-ha-dvr.html>` mode is enabled). In this case, ensure
``neutron_external_interface`` is configured correctly for hosts in the
``compute`` group.

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

   [securitygroup]
   firewall_driver = openvswitch

L3 agent high availability
~~~~~~~~~~~~~~~~~~~~~~~~~~

L3 and DHCP agents can be created in a high availability (HA) state with:

.. code-block:: yaml

   enable_neutron_agent_ha: "yes"

This allows networking to fail over across controllers if the active agent is
stopped. If this option is enabled, it can be advantageous to also set:

.. code-block:: yaml

   neutron_l3_agent_failover_delay:

Agents sometimes need to be restarted. This delay (in seconds) is invoked
between the restart operations of each agent. When set properly, it will stop
network outages caused by all agents restarting at the same time. The exact
length of time it takes to restart is dependent on hardware and the number of
routers present. A general rule of thumb is to set the value to ``40 + 3n``
where ``n`` is the number of routers. For example, with 5 routers,
``40 + (3 * 5) = 65`` so the value could be set to 65. A much better approach
however would be to first time how long an outage lasts, then set the value
accordingly.

The default value is 0. A nonzero starting value would only result in
outages if the failover time was greater than the delay, which would be more
difficult to diagnose than consistent behaviour.

OVN (ml2/ovn)
~~~~~~~~~~~~~

In order to use ``OVN`` as mechanism driver for ``neutron``, you need to set
the following:

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   neutron_plugin_agent: "ovn"

When using OVN - Kolla Ansible will not enable distributed floating ip
functionality (not enable external bridges on computes) by default.
To change this behaviour you need to set the following:

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   neutron_ovn_distributed_fip: "yes"

Similarly - in order to have Neutron DHCP agents deployed in OVN networking
scenario, use:

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   neutron_ovn_dhcp_agent: "yes"

This might be desired for example when Ironic bare metal nodes are
used as a compute service. Currently OVN is not able to answer DHCP
queries on port type external, this is where Neutron agent helps.

In order to deploy Neutron OVN Agent you need to set the following:

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   neutron_enable_ovn_agent: "yes"

Currently the agent is only needed for QoS for hardware offloaded ports.

Mellanox Infiniband (ml2/mlnx)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to add ``mlnx_infiniband`` to the list of mechanism driver
for ``neutron`` to support Infiniband virtual funtions, you need to
set the following (assuming neutron SR-IOV agent is also enabled using
``enable_neutron_sriov`` flag):

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   enable_neutron_mlnx: "yes"

Additionally, you will also need to provide physnet:interface mappings
via ``neutron_mlnx_physnet_mappings`` which is presented to
``neutron_mlnx_agent`` container via ``mlnx_agent.ini`` and
``neutron_eswitchd`` container via ``eswitchd.conf``:

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   neutron_mlnx_physnet_mappings:
     ibphysnet: "ib0"

SSH authentication in external systems (switches)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla, by default, generates and copies an ssh key to the ``neutron_server``
container (under ``/var/lib/neutron/.ssh/id_rsa``) which can be used for
authentication in external systems (e.g. in ``networking-generic-switch`` or
``networking-ansible`` managed switches).

You can set ``neutron_ssh_key`` variable in ``passwords.yml`` to control the
used key.

Custom Kernel Module Configuration for Neutron
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Neutron may require specific kernel modules for certain functionalities.
While there are predefined default modules in the Ansible role, users have
the flexibility to add custom modules as needed.

To add custom kernel modules for Neutron, modify the configuration in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   neutron_modules_extra:
     - name: 'nf_conntrack_tftp'
       params: 'hashsize=4096'

In this example:

- `neutron_modules_extra`: Allows users to specify additional modules and
  their associated parameters. The given configuration adjusts the
  `hashsize` parameter for the `nf_conntrack_tftp` module.
