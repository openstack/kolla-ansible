.. _mariadb-backup-and-restore:

===================================
MariaDB database backup and restore
===================================

Kolla Ansible can facilitate either full or incremental backups of data
hosted in MariaDB. It achieves this using Mariabackup, a tool
designed to allow for 'hot backups' - an approach which means that consistent
backups can be taken without any downtime for your database or your cloud.

.. note::

   By default, backups will be performed on the first node in your Galera cluster
   or on the MariaDB node itself if you just have the one. Backup files are saved
   to a dedicated Docker volume - ``mariadb_backup`` - and it's the contents of
   this that you should target for transferring backups elsewhere.

Enabling Backup Functionality
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For backups to work, some reconfiguration of MariaDB is required - this is to
enable appropriate permissions for the backup client, and also to create an
additional database in order to store backup information.

Firstly, enable backups via ``globals.yml``:

.. code-block:: console

   enable_mariabackup: "yes"

Then, kick off a reconfiguration of MariaDB:

``kolla-ansible reconfigure -i INVENTORY -t mariadb``

Once that has run successfully, you should then be able to take full and
incremental backups as described below.

Backup Procedure
~~~~~~~~~~~~~~~~

To perform a full backup, run the following command:

``kolla-ansible mariadb_backup -i INVENTORY``

Or to perform an incremental backup:

``kolla-ansible mariadb_backup  -i INVENTORY --incremental``

Kolla doesn't currently manage the scheduling of these backups, so you'll
need to configure an appropriate scheduler (i.e cron) to run these commands
on your behalf should you require regular snapshots of your data. A suggested
schedule would be:

* Daily full, retained for two weeks
* Hourly incremental, retained for one day

Backups are performed on your behalf on the designated database node using
permissions defined during the configuration step; no password is required to
invoke these commands.

Furthermore, backup actions can be triggered from a node with a minimal
installation of Kolla Ansible, specifically one which doesn't require a copy of
``passwords.yml``.  This is of note if you're looking to implement automated
backups scheduled via a cron job.

Restoring backups
~~~~~~~~~~~~~~~~~

Owing to the way in which Mariabackup performs hot backups, there are some
steps that must be performed in order to prepare your data before it can be
copied into place for use by MariaDB. This process is currently manual, but
the Kolla Mariabackup image includes the tooling necessary to successfully
prepare backups. Two examples are given below.

Full
----

For a full backup, start a new container using the Mariabackup image with the
following options on the first database node:

.. code-block:: console

   docker run --rm -it --volumes-from mariadb --name dbrestore \
      --volume mariadb_backup:/backup \
      quay.io/openstack.kolla/mariadb-server:|KOLLA_OPENSTACK_RELEASE|-rocky-10 \
      /bin/bash
   (dbrestore) $ cd /backup
   (dbrestore) $ rm -rf /backup/restore
   (dbrestore) $ mkdir -p /backup/restore/full
   (dbrestore) $ gunzip mysqlbackup-04-10-2018.qp.xbc.xbs.gz
   (dbrestore) $ mbstream -x -C /backup/restore/full/ < mysqlbackup-04-10-2018.qp.xbc.xbs
   (dbrestore) $ mariabackup --prepare --target-dir /backup/restore/full

Stop the MariaDB instance on all nodes:

.. code-block:: console

   kolla-ansible stop -i multinode -t mariadb --yes-i-really-really-mean-it

Delete the old data files (or move them elsewhere), and copy the backup into
place, again on the first node:

.. code-block:: console

   docker run --rm -it --volumes-from mariadb --name dbrestore \
      --volume mariadb_backup:/backup \
      quay.io/openstack.kolla/mariadb-server:|KOLLA_OPENSTACK_RELEASE|-rocky-10 \
      /bin/bash
   (dbrestore) $ rm -rf /var/lib/mysql/*
   (dbrestore) $ rm -rf /var/lib/mysql/\.[^\.]*
   (dbrestore) $ mariabackup --copy-back --target-dir /backup/restore/full

Then you can restart MariaDB with the restored data in place.

For single node deployments:

.. code-block:: console

   docker start mariadb
   docker logs mariadb
   81004 15:48:27 mysqld_safe WSREP: Running position recovery with --log_error='/var/lib/mysql//wsrep_recovery.BDTAm8' --pid-file='/var/lib/mysql//scratch-recover.pid'
   181004 15:48:30 mysqld_safe WSREP: Recovered position 9388319e-c7bd-11e8-b2ce-6e9ec70d9926:58

For multinode deployment restores, a MariaDB recovery role should be run,
pointing to the first node of the cluster:

.. code-block:: console

   kolla-ansible mariadb_recovery -i multinode -e mariadb_recover_inventory_name=controller1

The above procedure is valid also for a disaster recovery scenario. In such
case, first copy MariaDB backup file from the external source into
``mariadb_backup`` volume on the first node of the cluster. From there,
use the same steps as mentioned in the procedure above.

Incremental
-----------

This starts off similar to the full backup restore procedure above, but we
must apply the logs from the incremental backups first of all before doing
the final preparation required prior to restore. In the example below, I have
a full backup - ``mysqlbackup-06-11-2018-1541505206.qp.xbc.xbs``, and an
incremental backup,
``incremental-11-mysqlbackup-06-11-2018-1541505223.qp.xbc.xbs``.

.. code-block:: console

   docker run --rm -it --volumes-from mariadb --name dbrestore \
      --volume mariadb_backup:/backup --tmpfs /backup/restore \
      quay.io/openstack.kolla/mariadb-server:|KOLLA_OPENSTACK_RELEASE|-rocky-10 \
      /bin/bash
   (dbrestore) $ cd /backup
   (dbrestore) $ rm -rf /backup/restore
   (dbrestore) $ mkdir -p /backup/restore/full
   (dbrestore) $ mkdir -p /backup/restore/inc
   (dbrestore) $ gunzip mysqlbackup-06-11-2018-1541505206.qp.xbc.xbs.gz
   (dbrestore) $ gunzip incremental-11-mysqlbackup-06-11-2018-1541505223.qp.xbc.xbs.gz
   (dbrestore) $ mbstream -x -C /backup/restore/full/ < mysqlbackup-06-11-2018-1541505206.qp.xbc.xbs
   (dbrestore) $ mbstream -x -C /backup/restore/inc < incremental-11-mysqlbackup-06-11-2018-1541505223.qp.xbc.xbs
   (dbrestore) $ mariabackup --prepare --target-dir /backup/restore/full
   (dbrestore) $ mariabackup --prepare --incremental-dir=/backup/restore/inc --target-dir /backup/restore/full

At this point the backup is prepared and ready to be copied back into place,
as per the previous example.
