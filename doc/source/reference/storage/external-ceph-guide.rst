.. _external-ceph-guide:

=============
External Ceph
=============

Kolla Ansible does not provide support for provisioning and configuring a
Ceph cluster directly. Instead, administrators should use a tool dedicated
to this purpose, such as:

* `ceph-ansible <https://docs.ceph.com/projects/ceph-ansible/en/latest/>`_
* `cephadm <https://docs.ceph.com/en/latest/cephadm/install/>`_

The desired pool(s) and keyrings should then be created via the Ceph CLI
or similar.

Requirements
~~~~~~~~~~~~

* An existing installation of Ceph
* Existing Ceph storage pools
* Existing credentials in Ceph for OpenStack services to connect to Ceph
  (Glance, Cinder, Nova, Gnocchi, Manila)

Refer to https://docs.ceph.com/en/latest/rbd/rbd-openstack/ for details on
creating the pool and keyrings with appropriate permissions for each service.

Configuring External Ceph
~~~~~~~~~~~~~~~~~~~~~~~~~

Ceph integration is configured for different OpenStack services independently.

Glance
------

Ceph RBD can be used as a storage backend for Glance images. Configuring Glance
for Ceph includes the following steps:

#. Enable Glance Ceph backend in ``globals.yml``:

   .. code-block:: yaml

      glance_backend_ceph: "yes"

#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_glance_keyring`` (default: ``ceph.client.glance.keyring``)
   * ``ceph_glance_user`` (default: ``glance``)
   * ``ceph_glance_pool_name`` (default: ``images``)

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

#. Copy Ceph keyring to ``/etc/kolla/config/glance/<ceph_glance_keyring>``

Cinder
------

Ceph RBD can be used as a storage backend for Cinder volumes. Configuring
Cinder for Ceph includes following steps:

#. When using external Ceph, there may be no nodes defined in the storage
   group.  This will cause Cinder and related services relying on this group to
   fail.  In this case, operator should add some nodes to the storage group,
   all the nodes where ``cinder-volume`` and ``cinder-backup`` will run:

   .. code-block:: ini

      [storage]
      control01

#. Enable Cinder Ceph backend in ``globals.yml``:

   .. code-block:: yaml

      cinder_backend_ceph: "yes"

#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_cinder_keyring`` (default: ``ceph.client.cinder.keyring``)
   * ``ceph_cinder_user`` (default: ``cinder``)
   * ``ceph_cinder_pool_name`` (default: ``volumes``)
   * ``ceph_cinder_backup_keyring``
     (default: ``ceph.client.cinder-backup.keyring``)
   * ``ceph_cinder_backup_user`` (default: ``cinder-backup``)
   * ``ceph_cinder_backup_pool_name`` (default: ``backups``)

#. Copy Ceph configuration file to ``/etc/kolla/config/cinder/ceph.conf``

   Separate configuration options can be configured for
   cinder-volume and cinder-backup by adding ceph.conf files to
   ``/etc/kolla/config/cinder/cinder-volume`` and
   ``/etc/kolla/config/cinder/cinder-backup`` respectively. They
   will be merged with ``/etc/kolla/config/cinder/ceph.conf``.

#. Copy Ceph keyring files to:

   * ``/etc/kolla/config/cinder/cinder-volume/<ceph_cinder_keyring>``
   * ``/etc/kolla/config/cinder/cinder-backup/<ceph_cinder_keyring>``
   * ``/etc/kolla/config/cinder/cinder-backup/<ceph_cinder_backup_keyring>``

.. note::

    ``cinder-backup`` requires two keyrings for accessing volumes
    and backup pool.

Nova must also be configured to allow access to Cinder volumes:

#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_cinder_keyring`` (default: ``ceph.client.cinder.keyring``)

#. Copy Ceph keyring file(s) to:

   * ``/etc/kolla/config/nova/<ceph_cinder_keyring>``

Nova
----

Ceph RBD can be used as a storage backend for Nova instance ephemeral disks.
This avoids the requirement for local storage for instances on compute nodes.
It improves the performance of migration, since instances' ephemeral disks do
not need to be copied between hypervisors.

Configuring Nova for Ceph includes following steps:

#. Enable Nova Ceph backend in ``globals.yml``:

   .. code-block:: yaml

      nova_backend_ceph: "yes"

#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_nova_keyring`` (by default it's the same as
     ``ceph_cinder_keyring``)
   * ``ceph_nova_user`` (by default it's the same as ``ceph_cinder_user``)
   * ``ceph_nova_pool_name`` (default: ``vms``)

#. Copy Ceph configuration file to ``/etc/kolla/config/nova/ceph.conf``
#. Copy Ceph keyring file(s) to:

   * ``/etc/kolla/config/nova/<ceph_nova_keyring>``

   .. note::

      If you are using a Ceph deployment tool that generates separate Ceph
      keys for Cinder and Nova, you will need to override
      ``ceph_nova_keyring`` and ``ceph_nova_user`` to match.

Gnocchi
-------

Ceph object storage can be used as a storage backend for Gnocchi metrics.
Configuring Gnocchi for Ceph includes following steps:

#. Enable Gnocchi Ceph backend in ``globals.yml``:

   .. code-block:: yaml

      gnocchi_backend_storage: "ceph"

#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_gnocchi_keyring``
     (default: ``ceph.client.gnocchi.keyring``)
   * ``ceph_gnocchi_user`` (default: ``gnocchi``)
   * ``ceph_gnocchi_pool_name`` (default: ``gnocchi``)

#. Copy Ceph configuration file to ``/etc/kolla/config/gnocchi/ceph.conf``
#. Copy Ceph keyring to ``/etc/kolla/config/gnocchi/<ceph_gnocchi_keyring>``

Manila
------

CephFS can be used as a storage backend for Manila shares. Configuring Manila
for Ceph includes following steps:

#. Enable Manila Ceph backend in ``globals.yml``:

   .. code-block:: yaml

      enable_manila_backend_cephfs_native: "yes"

#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_manila_keyring`` (default: ``ceph.client.manila.keyring``)
   * ``ceph_manila_user`` (default: ``manila``)

   .. note::

      Required Ceph identity caps for manila user are documented in
      :manila-doc:`CephFS Native driver <admin/cephfs_driver.html#authorizing-the-driver-to-communicate-with-ceph>`.

   .. important::

      CephFS driver in the Wallaby (or later) release requires a Ceph identity
      with a different set of Ceph capabilities when compared to the driver
      in a pre-Wallaby release - please refer to Manila
      :manila-doc:`CephFS Native driver Documentation <admin/cephfs_driver.html#authorizing-the-driver-to-communicate-with-ceph>`.

#. Copy Ceph configuration file to ``/etc/kolla/config/manila/ceph.conf``
#. Copy Ceph keyring to ``/etc/kolla/config/manila/<ceph_manila_keyring>``

#. If using multiple filesystems (Ceph Pacific+), set
   ``manila_cephfs_filesystem_name`` in ``/etc/kolla/globals.yml`` to the
   name of the Ceph filesystem Manila should use.
   By default, Manila will use the first filesystem returned by
   the ``ceph fs volume ls`` command.

#. Setup Manila in the usual way

For more details on the rest of the Manila setup, such as creating the share
type ``default_share_type``, please see :doc:`Manila in Kolla <manila-guide>`.

For more details on the CephFS Native driver, please see
:manila-doc:`CephFS Native driver <admin/cephfs_driver.html>`.
