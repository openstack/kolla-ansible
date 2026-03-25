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
by the ``kolla-ansible mariadb-backup`` command. This will be improved
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

.. _mariadb-notifications:

Cluster Event Notifications
---------------------------

Kolla Ansible supports native MariaDB Galera cluster notifications. This allows
operators to execute custom logic whenever a node status or cluster membership
changes.

To enable this feature, you must provide a custom script named
``wsrep-notify.sh`` in the following directory on the control host:
``/etc/kolla/config/mariadb/wsrep-notify.sh``.

Kolla Ansible will automatically detect the presence of this file, copy it to
the MariaDB nodes, and configure the ``wsrep_notify_cmd`` directive in the
MariaDB configuration.

Example 1: Integration with Prometheus Alertmanager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use this feature to send alerts directly to Prometheus Alertmanager.
Save the following content as ``/etc/kolla/config/mariadb/wsrep-notify.sh``:

.. code-block:: bash

    #!/bin/bash

    # List of Alertmanager instances (direct IP addresses)
    # Using kolla_address to bypass VIP for higher reliability
    ALERTMANAGERS=(
    {% for host in groups['prometheus-alertmanager'] %}
      "{{ internal_protocol }}://{{ 'api' | kolla_address(host) |
      put_address_in_context('url') }}:{{ hostvars[host]
      ['prometheus_alertmanager_port'] }}/api/v2/alerts"
    {% endfor %}
    )

    # Authentication credentials from Kolla configuration
    AUTH="{{ prometheus_alertmanager_user }}:{{
    prometheus_alertmanager_password }}"
    HOSTNAME=$(hostname)

    # Prepare the JSON payload for the Alertmanager API
    PAYLOAD=$(cat <<EOF
    [
      {
        "labels": {
          "alertname": "GaleraEvent",
          "severity": "warning",
          "instance": "$HOSTNAME"
        },
        "annotations": {
          "description": "Galera cluster event detected: $*",
          "summary": "Galera Status Change on $HOSTNAME"
        }
      }
    ]
    EOF
    )

    # Iterate through instances until the first successful POST
    for URL in "${ALERTMANAGERS[@]}"; do
        echo "Attempting to send alert to: $URL"
        if curl -X POST "$URL" \
             -u "$AUTH" \
             -H "Content-Type: application/json" \
             -d "$PAYLOAD" \
             --fail --silent --show-error; then
            echo "Alert sent successfully."
            exit 0
        fi
        echo "Failed to reach $URL, trying next instance..."
    done

    echo "Error: Could not send alert to any Alertmanager instance."
    exit 1

.. note::

   When providing this script, ensure it has the correct permissions. Kolla
   Ansible will attempt to set execution permissions (``0755``) automatically
   during the deployment.

Example 2: Logging Cluster Changes to a File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Alternatively, you can log all cluster events to a local file for later audit
or simple monitoring. Save the following content as
``/etc/kolla/config/mariadb/wsrep-notify.sh``:

.. code-block:: bash

   #!/bin/bash

   LOG_FILE="/var/log/kolla/mariadb/galera_cluster_events.log"
   TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

   echo "[$TIMESTAMP] Host: $HOSTNAME | Event: $*" >> "$LOG_FILE"

.. note::

   When providing this script, ensure it has the correct permissions. Kolla
   Ansible will attempt to set execution permissions (``0755``) automatically
   during the deployment.
