.. _haproxy-guide:

=============
HAProxy Guide
=============

Kolla Ansible supports a Highly Available (HA) deployment of
Openstack and other services. High-availability in Kolla
is implented as via Keepalived and HAProxy. Keepalived manages virtual IP
addresses, while HAProxy load-balances traffic to service backends.
These two components must be installed on the same hosts
and they are deployed to hosts in the ``haproxy`` group.

Preparation and deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~

HAProxy and Keepalived are enabled by default. They may be disabled by
setting the following in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_haproxy: "no"
   enable_keepalived: "no"

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
