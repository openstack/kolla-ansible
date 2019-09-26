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

Refer to http://docs.ceph.com/docs/master/rbd/rbd-openstack/ for details on
creating the pool and keyrings with appropriate permissions for each service.

Enabling External Ceph
~~~~~~~~~~~~~~~~~~~~~~

Using external Ceph with Kolla means not to deploy Ceph via Kolla. Therefore,
disable Ceph deployment in ``/etc/kolla/globals.yml``

.. code-block:: yaml

   enable_ceph: "no"

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

Configuring External Ceph
~~~~~~~~~~~~~~~~~~~~~~~~~

Glance
------

Configuring Glance for Ceph includes the following steps:

#. Configure RBD back end in ``glance-api.conf``

   .. path /etc/kolla/config/glance/glance-api.conf
   .. code-block:: ini

      [glance_store]
      stores = rbd
      default_store = rbd
      rbd_store_pool = images
      rbd_store_user = glance
      rbd_store_ceph_conf = /etc/ceph/ceph.conf

#. Copy Ceph configuration file to ``/etc/kolla/config/glance/ceph.conf``

   .. path /etc/kolla/config/glance/ceph.conf
   .. code-block:: ini

      [global]
      fsid = 1d89fec3-325a-4963-a950-c4afedd37fe3
      mon_initial_members = ceph-0
      mon_host = 192.168.0.56
      auth_cluster_required = cephx
      auth_service_required = cephx
      auth_client_required = cephx

#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_glance_keyring`` (default: ``ceph.client.glance.keyring``)

#. Copy Ceph keyring to ``/etc/kolla/config/glance/<ceph_glance_keyring>``

Cinder
------

Configuring Cinder for Ceph includes following steps:

#. Configure RBD backend in ``cinder-volume.conf`` and ``cinder-backup.conf``

   .. path /etc/kolla/config/cinder/cinder-volume.conf
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

   .. note::

      ``cinder_rbd_secret_uuid`` can be found in ``/etc/kolla/passwords.yml``.

   .. path /etc/kolla/config/cinder/cinder-backup.conf
   .. code-block:: ini

      [DEFAULT]
      backup_ceph_conf=/etc/ceph/ceph.conf
      backup_ceph_user=cinder-backup
      backup_ceph_chunk_size = 134217728
      backup_ceph_pool=backups
      backup_driver = cinder.backup.drivers.ceph.CephBackupDriver
      backup_ceph_stripe_unit = 0
      backup_ceph_stripe_count = 0
      restore_discard_excess_bytes = true

   For more information about the Cinder backup configuration, see
   :cinder-doc:`Ceph backup driver
   <configuration/block-storage/backup/ceph-backup-driver.html>`.

#. Copy Ceph configuration file to ``/etc/kolla/config/cinder/ceph.conf``

   Separate configuration options can be configured for
   cinder-volume and cinder-backup by adding ceph.conf files to
   ``/etc/kolla/config/cinder/cinder-volume`` and
   ``/etc/kolla/config/cinder/cinder-backup`` respectively. They
   will be merged with ``/etc/kolla/config/cinder/ceph.conf``.

#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:
   * ``ceph_cinder_keyring`` (default: ``ceph.client.cinder.keyring``)
   * ``ceph_cinder_backup_keyring``
   (default: ``ceph.client.cinder-backup.keyring``)

#. Copy Ceph keyring files to:
   * ``/etc/kolla/config/cinder/cinder-volume/<ceph_cinder_keyring>``
   * ``/etc/kolla/config/cinder/cinder-backup/<ceph_cinder_keyring>``
   * ``/etc/kolla/config/cinder/cinder-backup/<ceph_cinder_backup_keyring>``

.. note::

    ``cinder-backup`` requires two keyrings for accessing volumes
    and backup pool.

Nova
----

Configuring Nova for Ceph includes following steps:

#. Copy Ceph configuration file to ``/etc/kolla/config/nova/ceph.conf``
#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_cinder_keyring`` (default: ``ceph.client.cinder.keyring``)
   * ``ceph_nova_keyring`` (by default it's the same as ceph_cinder_keyring)

#. Copy Ceph keyring file(s) to:

   * ``/etc/kolla/config/nova/<ceph_cinder_keyring>``
   * ``/etc/kolla/config/nova/<ceph_nova_keyring>`` (if your Ceph deployment
     created one)

   .. warning::

      If you are using ceph-ansible or another deployment tool that doesn't
      create separate key for Nova just copy the Cinder key.

#. Configure nova-compute to use Ceph as the ephemeral back end by creating
   ``/etc/kolla/config/nova/nova-compute.conf`` and adding the following
   configurations:

   .. code-block:: ini

      [libvirt]
      images_rbd_pool=vms
      images_type=rbd
      images_rbd_ceph_conf=/etc/ceph/ceph.conf

Gnocchi
-------

Configuring Gnocchi for Ceph includes following steps:

#. Copy Ceph configuration file to ``/etc/kolla/config/gnocchi/ceph.conf``
#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_gnocchi_keyring``
     (default: ``ceph.client.gnocchi.keyring``)

#. Copy Ceph keyring to ``/etc/kolla/config/gnocchi/<ceph_gnocchi_keyring>``
#. Modify ``/etc/kolla/config/gnocchi.conf`` file according to the following
   configuration:

   .. code-block:: ini

      [storage]
      driver = ceph
      ceph_username = gnocchi
      ceph_keyring = /etc/ceph/ceph.client.gnocchi.keyring
      ceph_conffile = /etc/ceph/ceph.conf

Manila
------

Configuring Manila for Ceph includes following steps:

#. Configure CephFS backend by setting ``enable_manila_backend_cephfs_native``
   to ``true``
#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_manila_keyring`` (default: ``ceph.client.manila.keyring``)

#. Copy Ceph configuration file to ``/etc/kolla/config/manila/ceph.conf``
#. Copy Ceph keyring to ``/etc/kolla/config/manila/<ceph_manila_keyring>``
#. Setup Manila in the usual way

For more details on the rest of the Manila setup, such as creating the share
type ``default_share_type``, please see :doc:`Manila in Kolla <manila-guide>`.

For more details on the CephFS Native driver, please see
:manila-doc:`CephFS driver <admin/cephfs_driver.html>`.
