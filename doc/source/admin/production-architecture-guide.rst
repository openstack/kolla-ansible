.. architecture-guide:

=============================
Production architecture guide
=============================

This guide will help with configuring Kolla to suit production needs. It is
meant to answer some questions regarding basic configuration options that Kolla
requires. This document also contains other useful pointers.

Node types and services running on them
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A basic Kolla inventory consists of several types of nodes, known in Ansible as
``groups``.

* Control - Cloud controller nodes which host control services
  like APIs and databases. This group should have odd number of nodes for
  quorum.

* Network - Network nodes host Neutron agents along with
  haproxy / keepalived. These nodes will have a floating ip defined in
  ``kolla_internal_vip_address``.

* Compute - Compute nodes for compute services. This is where guest VMs
  live.

* Storage - Storage nodes for cinder-volume, LVM.

* Monitoring - Monitor nodes which host monitoring services.

Network configuration
~~~~~~~~~~~~~~~~~~~~~

.. _interface-configuration:

Interface configuration
-----------------------

In Kolla operators should configure following network interfaces:

* ``network_interface`` - While it is not used on its own, this provides the
  required default for other interfaces below.

* ``api_interface`` - This interface is used for the management network. The
  management network is the network OpenStack services uses to communicate to
  each other and the databases. There are known security risks here, so it's
  recommended to make this network internal, not accessible from outside.
  Defaults to ``network_interface``.

* ``kolla_external_vip_interface`` - This interface is public-facing one. It's
  used when you want HAProxy public endpoints to be exposed in different
  network than internal ones. It is mandatory to set this option when
  ``kolla_enable_tls_external`` is set to yes. Defaults to
  ``network_interface``.

* ``tunnel_interface`` - This interface is used by Neutron for vm-to-vm traffic
  over tunneled networks (like VxLan). Defaults to ``network_interface``.

* ``neutron_external_interface`` - This interface is required by Neutron.
  Neutron will put br-ex on it. It will be used for flat networking as well as
  tagged vlan networks. Has to be set separately.

* ``dns_interface`` - This interface is required by Designate and Bind9.
  Is used by public facing DNS requests and queries to bind9 and designate
  mDNS services. Defaults to ``network_interface``.

* ``bifrost_network_interface`` - This interface is required by Bifrost.
  Is used to provision bare metal cloud hosts, require L2 connectivity
  with the bare metal cloud hosts in order to provide DHCP leases with
  PXE boot options. Defaults to ``network_interface``.

.. _address-family-configuration:

Address family configuration (IPv4/IPv6)
----------------------------------------

Starting with the Train release, Kolla Ansible allows operators to deploy
the control plane using IPv6 instead of IPv4. Each Kolla Ansible network
(as represented by interfaces) provides a choice of two address families.
Both internal and external VIP addresses can be configured using an IPv6
address as well.
IPv6 is tested on all supported platforms.

.. warning::

   While Kolla Ansible Train requires Ansible 2.6 or later, IPv6 support requires
   Ansible 2.8 or later due to a bug:
   https://github.com/ansible/ansible/issues/63227

.. note::

   Currently there is no dual stack support. IPv4 can be mixed with IPv6 only
   when on different networks. This constraint arises from services requiring
   common single address family addressing.

For example, ``network_address_family`` accepts either ``ipv4`` or ``ipv6``
as its value and defines the default address family for all networks just
like ``network_interface`` defines the default interface.
Analogically, ``api_address_family`` changes the address family for the API
network. Current listing of networks is available in ``globals.yml`` file.

.. note::

   While IPv6 support introduced in Train is broad, some services are known
   not to work yet with IPv6 or have some known quirks:

   * Bifrost does not support IPv6:
     https://storyboard.openstack.org/#!/story/2006689

   * Docker does not allow IPv6 registry address:
     https://github.com/moby/moby/issues/39033
     - the workaround is to use the hostname

   * Ironic DHCP server, dnsmasq, is not currently automatically configured
     to offer DHCPv6: https://bugs.launchpad.net/kolla-ansible/+bug/1848454

Docker configuration
~~~~~~~~~~~~~~~~~~~~

Because Docker is core dependency of Kolla, proper configuration of Docker can
change the experience of Kolla significantly. Following section will highlight
several Docker configuration details relevant to Kolla operators.

Storage driver
--------------

While the default storage driver should be fine for most users, Docker offers
more options to consider. For details please refer to
`Docker documentation <https://docs.docker.com/engine/userguide/storagedriver/selectadriver/>`_.

Volumes
-------

Kolla puts nearly all of persistent data in Docker volumes. These volumes are
created in Docker working directory, which defaults to ``/var/lib/docker``
directory.

We recommend to ensure that this directory has enough space and is placed on
fast disk as it will affect performance of builds, deploys as well as database
commits and rabbitmq.

This becomes especially relevant when ``enable_central_logging`` and
``openstack_logging_debug`` are both set to true, as fully loaded 130 node
cluster produced 30-50GB of logs daily.

High Availability (HA) and scalability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

HA is an important topic in production systems.
HA concerns itself with redundant instances of services so that the overall
service can be provided with close-to-zero interruption in case of failure.
Scalability often works hand-in-hand with HA to provide load sharing by
the use of load balancers.

OpenStack services
------------------

Multinode Kolla Ansible deployments provide HA and scalability for services.
OpenStack API endpoints are a prime example here: redundant ``haproxy``
instances provide HA with ``keepalived`` while the backends are also
deployed redundantly to enable both HA and load balancing.

Other core services
-------------------

The core non-OpenStack components required by most deployments: the SQL
database provided by ``mariadb`` and message queue provided by
``rabbitmq`` are also deployed in a HA way. Care has to be taken, however,
as unlike previously described services, these have more complex HA
mechanisms. The reason for that is that they provide the central, persistent
storage of information about the cloud that each other service assumes to
have a consistent state (aka integrity).
This assumption leads to the requirement of quorum establishment
(look up the CAP theorem for greater insight).

Quorum needs a majority vote and hence deploying 2 instances of these
do not provide (by default) any HA as a failure of one causes a failure
of the other one. Hence the recommended number of instances is ``3``,
where 1 node failure is acceptable. For scaling purposes and better
resilience it is possible to use ``5`` nodes and have 2 failures
acceptable.
Note, however, that higher numbers usually provide no benefits due to amount
of communication between quorum members themselves and the non-zero
probability of the communication medium failure happening instead.
