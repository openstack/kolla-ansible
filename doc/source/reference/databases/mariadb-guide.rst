.. _mariadb-guide:

=============
MariaDB Guide
=============

Kolla Ansible supports deployment of a MariaDB/Galera cluster
for use by OpenStack and other services.

MariaDB Shards
~~~~~~~~~~~~~~

A database shard, or simply a shard, is a horizontal partition of data
in a database or search engine. Each shard is held on a separate database
server/cluster, to spread load. Some data within a database remains present
in all shards, but some appears only in a single shard.
Each shard acts as the single source for this subset of data.

Kolla supports sharding on service's database level, so every database
can be hosted on different shard. Each shard is implemented as
an independent Galera cluster.

This section explains how to configure multiple database shards. Currently,
only one shard is accessible via the HAProxy load balancer and supported
by the ``kolla-ansible mariadb_backup`` command. This will be improved
in future by using ProxySQL, allowing load balanced access to all shards.

Deployment
----------

Each shard is identified by an integer ID, defined by ``mariadb_shard_id``.
The default shard, defined by ``mariadb_default_database_shard_id``
(default 0), identifies the shard that will be accessible via HAProxy and
available for backing up.

In order to deploy several MariaDB cluster, you will need to edit
inventory file in the way described below:

   .. code-block:: ini

      [mariadb]
      server1ofcluster0
      server2ofcluster0
      server3ofcluster0
      server1ofcluster1 mariadb_shard_id=1
      server2ofcluster1 mariadb_shard_id=1
      server3ofcluster1 mariadb_shard_id=1
      server1ofcluster2 mariadb_shard_id=2
      server2ofcluster2 mariadb_shard_id=2
      server3ofcluster2 mariadb_shard_id=2

.. note::

   If ``mariadb_shard_id`` is not defined for host in inventory file it will be set automatically
   to ``mariadb_default_database_shard_id`` (default 0) from ``group_vars/all/mariadb.yml`` and
   can be overwritten in ``/etc/kolla/globals.yml``. Shard which is marked as default is
   special in case of backup or loadbalance, as it is described below.

Loadbalancer
------------
Kolla currently supports balancing only for default shard. This will be
changed in future by replacement of HAProxy with ProxySQL. This results in
certain limitations as described below.

Backup and restore
------------------

Backup and restore is working only for default shard as kolla currently
using HAProxy solution for MariaDB loadbalancer which is simple TCP and
has configured only default shard hosts as backends, therefore backup
script will reach only default shard on ``kolla_internal_vip_address``.
