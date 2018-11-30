.. _opendaylight:

=============================
Opendaylight - SDN controller
=============================

Preparation and deployment
--------------------------

Modify the ``/etc/kolla/globals.yml`` file as the following example shows:

.. code-block:: yaml

   enable_opendaylight: "yes"
   neutron_plugin_agent: "opendaylight"

Networking-ODL is an additional Neutron plugin that allows the OpenDaylight
SDN Controller to utilize its networking virtualization features.
For OpenDaylight to work, the Networking-ODL plugin has to be installed in
the ``neutron-server`` container. In this case, one could use the
neutron-server-opendaylight container and the opendaylight container by
pulling from Kolla dockerhub or by building them locally.

OpenDaylight ``globals.yml`` configurable options with their defaults include:

.. code-block:: yaml

   opendaylight_mechanism_driver: "opendaylight_v2"
   opendaylight_l3_service_plugin: "odl-router_v2"
   opendaylight_acl_impl: "learn"
   enable_opendaylight_qos: "no"
   enable_opendaylight_l3: "yes"
   enable_opendaylight_legacy_netvirt_conntrack: "no"
   opendaylight_port_binding_type: "pseudo-agentdb-binding"
   opendaylight_features: "odl-mdsal-apidocs,odl-netvirt-openstack"
   opendaylight_allowed_network_types: '"flat", "vlan", "vxlan"'

Clustered OpenDaylight Deploy
-----------------------------

High availability clustered OpenDaylight requires modifying the inventory file
and placing three or more hosts in the OpenDaylight or Networking groups.

.. note::

   The OpenDaylight role will allow deploy of one or three plus hosts for
   OpenDaylight/Networking role.

Verification
------------

Verify the build and deploy operation of Networking-ODL containers. Successful
deployment will bring up an Opendaylight container in the list of running
containers on network/opendaylight node.

For the source code, please refer to the following link:
https://github.com/openstack/networking-odl
