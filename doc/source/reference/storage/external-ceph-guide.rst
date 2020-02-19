.. _external-ceph-guide:

=============
External Ceph
=============

Kolla Ansible does not provide support for provisioning and configuring a
Ceph cluster directly. Instead, administrators should use a tool dedicated
to this purpose, such as:

* `ceph-ansible <https://docs.ceph.com/ceph-ansible>`_
* `ceph-deploy <https://docs.ceph.com/docs/master/start/>`_
* `cephadm <https://docs.ceph.com/docs/master/bootstrap/>`_

The desired pool(s) and keyrings should then be created via the Ceph CLI
or similar.

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

To activate external Ceph integration you need to enable Ceph backend.
This can be done individually per service in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   glance_backend_ceph: "yes"
   cinder_backend_ceph: "yes"
   nova_backend_ceph: "yes"
   gnocchi_backend_storage: "ceph"
   enable_manila_backend_cephfs_native: "yes"

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

Configuring Cinder for Ceph includes following steps:

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

Nova
----

Configuring Nova for Ceph includes following steps:

#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_cinder_keyring`` (default: ``ceph.client.cinder.keyring``)
   * ``ceph_nova_keyring`` (by default it's the same as ceph_cinder_keyring)
   * ``ceph_nova_user`` (default: ``nova``)
   * ``ceph_nova_pool_name`` (default: ``vms``)

#. Copy Ceph configuration file to ``/etc/kolla/config/nova/ceph.conf``
#. Copy Ceph keyring file(s) to:

   * ``/etc/kolla/config/nova/<ceph_cinder_keyring>``
   * ``/etc/kolla/config/nova/<ceph_nova_keyring>`` (if your Ceph deployment
     created one)

   .. warning::

      If you are using ceph-ansible or another deployment tool that doesn't
      create separate key for Nova just copy the Cinder key and configure
      ``ceph_nova_user`` to the same value as ``ceph_cinder_user``.

Gnocchi
-------

Configuring Gnocchi for Ceph includes following steps:

#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_gnocchi_keyring``
     (default: ``ceph.client.gnocchi.keyring``)
   * ``ceph_gnocchi_user`` (default: ``gnocchi``)
   * ``ceph_gnocchi_pool_name`` (default: ``gnocchi``)

#. Copy Ceph configuration file to ``/etc/kolla/config/gnocchi/ceph.conf``
#. Copy Ceph keyring to ``/etc/kolla/config/gnocchi/<ceph_gnocchi_keyring>``

Manila
------

Configuring Manila for Ceph includes following steps:

#. Configure CephFS backend by setting ``enable_manila_backend_cephfs_native``
   to ``true``
#. Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

   * ``ceph_manila_keyring`` (default: ``ceph.client.manila.keyring``)
   * ``ceph_manila_user`` (default: ``manila``)

   .. note::

      Required Ceph identity caps for manila user are documented in
      :manila-doc:`CephFS Native driver <admin/cephfs_driver.html#authorizing-the-driver-to-communicate-with-ceph>`.

#. Copy Ceph configuration file to ``/etc/kolla/config/manila/ceph.conf``
#. Copy Ceph keyring to ``/etc/kolla/config/manila/<ceph_manila_keyring>``
#. Setup Manila in the usual way

For more details on the rest of the Manila setup, such as creating the share
type ``default_share_type``, please see :doc:`Manila in Kolla <manila-guide>`.

For more details on the CephFS Native driver, please see
:manila-doc:`CephFS Native driver <admin/cephfs_driver.html>`.
