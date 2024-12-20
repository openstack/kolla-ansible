.. _haproxy-guide:

=============
HAProxy Guide
=============

Kolla Ansible supports a Highly Available (HA) deployment of
Openstack and other services. High-availability in Kolla
is implemented as via Keepalived and HAProxy. Keepalived manages virtual IP
addresses, while HAProxy load-balances traffic to service backends.
These two components must be installed on the same hosts
and they are deployed to hosts in the ``loadbalancer`` group.

Preparation and deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~

HAProxy and Keepalived are enabled by default. They may be disabled by
setting the following in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_haproxy: "no"
   enable_keepalived: "no"

Single external frontend for services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Single external frontend for particular service can be enabled by adding the
following in ``/etc/kolla/globals.yml`` (feature and example services):

.. code-block:: yaml

   haproxy_single_external_frontend: true

   nova_external_fqdn: "nova.example.com"
   neutron_external_fqdn: "neutron.example.com"
   horizon_external_fqdn: "horizon.example.com"
   opensearch_external_fqdn: "opensearch.example.com"
   grafana_external_fqdn: "grafana.example.com"


The abovementioned functionality allows for exposing of services on separate
fqdns on commonly used port i.e. 443 instead of the usual high ports.

Configuration
~~~~~~~~~~~~~

Failover tuning
---------------

When a VIP fails over from one host to another, hosts may take some
time to detect that the connection has been dropped. This can lead
to service downtime.

To reduce the time by the kernel to close dead connections to VIP
address, modify the ``net.ipv4.tcp_retries2`` kernel option by setting
the following in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   haproxy_host_ipv4_tcp_retries2: 6

This is especially helpful for connections to MariaDB. See
`here <https://pracucci.com/linux-tcp-rto-min-max-and-tcp-retries2.html>`__,
`here <https://blog.cloudflare.com/when-tcp-sockets-refuse-to-die/>`__ and
`here <https://access.redhat.com/solutions/726753>`__ for
further information about this kernel option.

Backend weights
---------------

When different baremetal are used in infrastructure as haproxy backends
or they are overloaded for some reason, kolla-ansible is able to change
weight of backend per service. Weight can be any integer value from 1 to
256.

To set weight of backend per service, modify inventory file as below:

.. code-block:: ini

   [control]
   server1 haproxy_nova_api_weight=10
   server2 haproxy_nova_api_weight=2 haproxy_keystone_internal_weight=10
   server3 haproxy_keystone_admin_weight=50

HTTP/2 Support
---------------

HAProxy with HTTP/2 frontend support is enabled by default. It may be
disabled by setting the following in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   haproxy_enable_http2: "no"

SSL/TLS Settings
----------------

For SSL/TLS related settings refer to the :ref:`haproxy-tls-settings` section.
