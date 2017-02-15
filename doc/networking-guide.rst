.. _networking-guide:

============================
Enabling Neutron Extensions
============================

Overview
========
Kolla deploys Neutron by default as OpenStack networking component. This guide
describes configuring and running Neutron extensions like LBaaS,
Networking-SFC, QoS, etc.

Networking-SFC
==============

Preparation and deployment
--------------------------

Modify the configuration file ``/etc/kolla/globals.yml`` and change
the following:

::

    neutron_plugin_agent: "sfc"

Networking-SFC is an additional Neutron plugin. For SFC to work, this plugin
has to be installed in ``neutron-server`` container as well. Modify the
configuration file ``/etc/kolla/kolla-build.conf`` and add the following
contents:

::

    [neutron-server-plugin-networking-sfc]
    type = git
    location = https://github.com/openstack/networking-sfc.git
    reference = mitaka

Verification
------------

Verify the build and deploy operation of Networking-SFC container. Successful
deployment will bring up an SFC container in the list of running containers.
Run the following command to login into the ``neutron-server`` container:

::

    docker exec -it neutron_server bash

Neutron should provide the following CLI extensions.

::

    #neutron help|grep port

    port-chain-create                 [port_chain] Create a Port Chain.
    port-chain-delete                 [port_chain] Delete a given Port Chain.
    port-chain-list                   [port_chain] List Port Chains that belong
                                      to a given tenant.
    port-chain-show                   [port_chain] Show information of a
                                      given Port Chain.
    port-chain-update                 [port_chain] Update Port Chain's
                                      information.
    port-pair-create                  [port_pair] Create a Port Pair.
    port-pair-delete                  [port_pair] Delete a given Port Pair.
    port-pair-group-create            [port_pair_group] Create a Port Pair
                                      Group.
    port-pair-group-delete            [port_pair_group] Delete a given
                                      Port Pair Group.
    port-pair-group-list              [port_pair_group] List Port Pair Groups
                                      that belongs to a given tenant.
    port-pair-group-show              [port_pair_group] Show information of a
                                      given Port Pair Group.
    port-pair-group-update            [port_pair_group] Update Port Pair
                                      Group's information.
    port-pair-list                    [port_pair] List Port Pairs that belongs
                                      to a given tenant.
    port-pair-show                    [port_pair] Show information of a given
                                      Port Pair.
    port-pair-update                  [port_pair] Update Port Pair's
                                      information.

For setting up a testbed environment and creating a port chain, please refer
to the following link:

    https://wiki.openstack.org/wiki/Neutron/ServiceInsertionAndChaining

For the source code, please refer to the following link:

    https://github.com/openstack/networking-sfc


Neutron VPNaaS (VPN-as-a-Service)
=================================

Preparation and deployment
--------------------------

Modify the configuration file ``/etc/kolla/globals.yml`` and change
the following:

::

    enable_neutron_vpnaas: "yes"

Verification
------------

VPNaaS is a complex subject, hence this document provides directions for a
simple smoke test to verify the service is up and running.

On the network node(s), the ``neutron_vpnaas_agent`` should be up (image naming
and versioning may differ depending on deploy configuration):

::

    docker ps --filter name=neutron_vpnaas_agent
    CONTAINER ID        IMAGE
    COMMAND             CREATED             STATUS              PORTS
    NAMES
    97d25657d55e
    operator:5000/kolla/oraclelinux-source-neutron-vpnaas-agent:4.0.0
    "kolla_start"       44 minutes ago      Up 44 minutes
    neutron_vpnaas_agent

kolla-ansible includes a small script that can be used in tandem with
``tools/init-runonce`` to verify the VPN using two routers and two Nova VMs:

::

    tools/init-runonce
    tools/init-vpn

Verify both VPN services are active:

::

    neutron vpn-service-list
    +--------------------------------------+----------+--------------------------------------+--------+
    | id                                   | name     | router_id                            | status |
    +--------------------------------------+----------+--------------------------------------+--------+
    | ad941ec4-5f3d-4a30-aae2-1ab3f4347eb1 | vpn_west | 051f7ce3-4301-43cc-bfbd-7ffd59af539e | ACTIVE |
    | edce15db-696f-46d8-9bad-03d087f1f682 | vpn_east | 058842e0-1d01-4230-af8d-0ba6d0da8b1f | ACTIVE |
    +--------------------------------------+----------+--------------------------------------+--------+

Two VMs can now be booted, one on vpn_east, the other on vpn_west, and
encrypted ping packets observed being sent from one to the other.

For more information on this and VPNaaS in Neutron refer to the VPNaaS area on
the OpenStack wiki:

    https://wiki.openstack.org/wiki/Neutron/VPNaaS/HowToInstall
    https://wiki.openstack.org/wiki/Neutron/VPNaaS

