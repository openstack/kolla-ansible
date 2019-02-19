.. _external-ceph-guide:

=============
External Ceph
=============

Sometimes it is necessary to connect OpenStack services to an existing Ceph
cluster instead of deploying it with Kolla. This can be achieved with only a
few configuration steps in Kolla.

Requirements
~~~~~~~~~~~~

* An existing installation of Ceph
* Existing Ceph storage pools
* Existing credentials in Ceph for OpenStack services to connect to Ceph
  (Glance, Cinder, Nova, Gnocchi, Manila)

Enabling External Ceph
~~~~~~~~~~~~~~~~~~~~~~

Using external Ceph with Kolla means not to deploy Ceph via Kolla. Therefore,
disable Ceph deployment in ``/etc/kolla/globals.yml``

.. code-block:: yaml

   enable_ceph: "no"

.. end

There are flags indicating individual services to use ceph or not which default
to the value of ``enable_ceph``. Those flags now need to be activated in order
to activate external Ceph integration. This can be done individually per
service in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   glance_backend_ceph: "yes"
   cinder_backend_ceph: "yes"
   nova_backend_ceph: "yes"
   gnocchi_backend_storage: "ceph"
   enable_manila_backend_cephfs_native: "yes"

.. end

The combination of ``enable_ceph: "no"`` and ``<service>_backend_ceph: "yes"``
triggers the activation of external ceph mechanism in Kolla.

Edit the Inventory File
~~~~~~~~~~~~~~~~~~~~~~~

When using external Ceph, there may be no nodes defined in the storage group.
This will cause Cinder and related services relying on this group to fail.
In this case, operator should add some nodes to the storage group, all the
nodes where ``cinder-volume`` and ``cinder-backup`` will run:

.. code-block:: ini

   [storage]
   compute01

.. end

Configuring External Ceph
~~~~~~~~~~~~~~~~~~~~~~~~~

Glance
------

Configuring Glance for Ceph includes three steps:

#. Configure RBD back end in ``glance-api.conf``
#. Create Ceph configuration file in ``/etc/ceph/ceph.conf``
#. Create Ceph keyring file in ``/etc/ceph/ceph.client.<username>.keyring``

Step 1 is done by using Kolla's INI merge mechanism: Create a file in
``/etc/kolla/config/glance/glance-api.conf`` with the following contents:

.. code-block:: ini

   [glance_store]
   stores = rbd
   default_store = rbd
   rbd_store_pool = images
   rbd_store_user = glance
   rbd_store_ceph_conf = /etc/ceph/ceph.conf

.. end

Now put ceph.conf and the keyring file (name depends on the username created in
Ceph) into the same directory, for example:

.. path /etc/kolla/config/glance/ceph.conf
.. code-block:: ini

   [global]
   fsid = 1d89fec3-325a-4963-a950-c4afedd37fe3
   mon_initial_members = ceph-0
   mon_host = 192.168.0.56
   auth_cluster_required = cephx
   auth_service_required = cephx
   auth_client_required = cephx

.. end

.. code-block:: console

   $ cat /etc/kolla/config/glance/ceph.client.glance.keyring

   [client.glance]
   key = AQAg5YRXS0qxLRAAXe6a4R1a15AoRx7ft80DhA==

.. end

Kolla will pick up all files named ``ceph.*`` in this directory and copy them
to the ``/etc/ceph/`` directory of the container.

Cinder
------

Configuring external Ceph for Cinder works very similar to
Glance.

Modify ``/etc/kolla/config/cinder/cinder-volume.conf`` file according to
the following configuration:

.. code-block:: ini

   [DEFAULT]
   enabled_backends=rbd-1

   [rbd-1]
   rbd_ceph_conf=/etc/ceph/ceph.conf
   rbd_user=cinder
   backend_host=rbd:volumes
   rbd_pool=volumes
   volume_backend_name=rbd-1
   volume_driver=cinder.volume.drivers.rbd.RBDDriver
   rbd_secret_uuid = {{ cinder_rbd_secret_uuid }}

.. end

.. note::

   ``cinder_rbd_secret_uuid`` can be found in ``/etc/kolla/passwords.yml`` file.

Modify ``/etc/kolla/config/cinder/cinder-backup.conf`` file according to
the following configuration:

.. code-block:: ini

   [DEFAULT]
   backup_ceph_conf=/etc/ceph/ceph.conf
   backup_ceph_user=cinder-backup
   backup_ceph_chunk_size = 134217728
   backup_ceph_pool=backups
   backup_driver = cinder.backup.drivers.ceph
   backup_ceph_stripe_unit = 0
   backup_ceph_stripe_count = 0
   restore_discard_excess_bytes = true

.. end

Next, copy the ``ceph.conf`` file into ``/etc/kolla/config/cinder/``:

.. code-block:: ini

   [global]
   fsid = 1d89fec3-325a-4963-a950-c4afedd37fe3
   mon_initial_members = ceph-0
   mon_host = 192.168.0.56
   auth_cluster_required = cephx
   auth_service_required = cephx
   auth_client_required = cephx

.. end

Separate configuration options can be configured for
cinder-volume and cinder-backup by adding ceph.conf files to
``/etc/kolla/config/cinder/cinder-volume`` and
``/etc/kolla/config/cinder/cinder-backup`` respectively. They
will be merged with ``/etc/kolla/config/cinder/ceph.conf``.

Ceph keyrings are deployed per service and placed into
``cinder-volume`` and ``cinder-backup`` directories, put the keyring files
to these directories, for example:

.. note::

    ``cinder-backup`` requires two keyrings for accessing volumes
    and backup pool.

.. code-block:: console

   $ cat /etc/kolla/config/cinder/cinder-backup/ceph.client.cinder.keyring

   [client.cinder]
   key = AQAg5YRXpChaGRAAlTSCleesthCRmCYrfQVX1w==

.. end

.. code-block:: console

   $ cat /etc/kolla/config/cinder/cinder-backup/ceph.client.cinder-backup.keyring

   [client.cinder-backup]
   key = AQC9wNBYrD8MOBAAwUlCdPKxWZlhkrWIDE1J/w==

.. end

.. code-block:: console

   $ cat /etc/kolla/config/cinder/cinder-volume/ceph.client.cinder.keyring

   [client.cinder]
   key = AQAg5YRXpChaGRAAlTSCleesthCRmCYrfQVX1w==

.. end

It is important that the files are named ``ceph.client*``.

Nova
----

Put ceph.conf, nova client keyring file and cinder client keyring file into
``/etc/kolla/config/nova``:

.. code-block:: console

   $ ls /etc/kolla/config/nova
   ceph.client.cinder.keyring ceph.client.nova.keyring ceph.conf

.. end

Configure nova-compute to use Ceph as the ephemeral back end by creating
``/etc/kolla/config/nova/nova-compute.conf`` and adding the following
configurations:

.. code-block:: ini

   [libvirt]
   images_rbd_pool=vms
   images_type=rbd
   images_rbd_ceph_conf=/etc/ceph/ceph.conf
   rbd_user=nova

.. end

.. note::

   ``rbd_user`` might vary depending on your environment.

Gnocchi
-------

Modify ``/etc/kolla/config/gnocchi/gnocchi.conf`` file according to
the following configuration:

.. code-block:: ini

   [storage]
   driver = ceph
   ceph_username = gnocchi
   ceph_keyring = /etc/ceph/ceph.client.gnocchi.keyring
   ceph_conffile = /etc/ceph/ceph.conf

.. end

Put ceph.conf and gnocchi client keyring file in
``/etc/kolla/config/gnocchi``:

.. code-block:: console

   $ ls /etc/kolla/config/gnocchi
   ceph.client.gnocchi.keyring ceph.conf gnocchi.conf

.. end

Manila
------

Configuring Manila for Ceph includes four steps:

#. Configure CephFS backend, setting ``enable_manila_backend_cephfs_native``
#. Create Ceph configuration file in ``/etc/ceph/ceph.conf``
#. Create Ceph keyring file in ``/etc/ceph/ceph.client.<username>.keyring``
#. Setup Manila in the usual way

Step 1 is done by using setting ``enable_manila_backend_cephfs_native=true``

Now put ceph.conf and the keyring file (name depends on the username created
in Ceph) into the same directory, for example:

.. path /etc/kolla/config/manila/ceph.conf
.. code-block:: ini

   [global]
   fsid = 1d89fec3-325a-4963-a950-c4afedd37fe3
   mon_host = 192.168.0.56
   auth_cluster_required = cephx
   auth_service_required = cephx
   auth_client_required = cephx

.. end

.. code-block:: console

   $ cat /etc/kolla/config/manila/ceph.client.manila.keyring

   [client.manila]
   key = AQAg5YRXS0qxLRAAXe6a4R1a15AoRx7ft80DhA==

.. end

For more details on the rest of the Manila setup, such as creating the share
type ``default_share_type``, please see :doc:`Manila in Kolla <manila-guide>`.

For more details on the CephFS Native driver, please see `CephFS driver
<https://docs.openstack.org/manila/latest/admin/cephfs_driver.html>`__.
