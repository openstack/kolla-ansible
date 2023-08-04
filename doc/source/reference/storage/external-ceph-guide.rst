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

.. note::

    Commands like ``ceph config generate-minimal-conf`` generate configuration
    files that have leading tabs. These tabs break Kolla Ansible's ini parser.
    Be sure to remove the leading tabs from your ``ceph.conf`` files when
    copying them in the following sections.


Glance
------

Ceph RBD can be used as a storage backend for Glance images. Configuring Glance
for Ceph includes the following steps:

* Enable Glance Ceph backend in ``globals.yml``:

  .. code-block:: yaml

     glance_backend_ceph: "yes"

* Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

  * ``ceph_glance_keyring`` (default: ``client.glance.keyring``)
  * ``ceph_glance_user`` (default: ``glance``)
  * ``ceph_glance_pool_name`` (default: ``images``)

* Copy Ceph configuration file to ``/etc/kolla/config/glance/ceph.conf``

  .. path /etc/kolla/config/glance/ceph.conf
  .. code-block:: ini

     [global]
     fsid = 1d89fec3-325a-4963-a950-c4afedd37fe3
     keyring = /etc/ceph/ceph.client.glance.keyring
     mon_initial_members = ceph-0
     mon_host = 192.168.0.56
     auth_cluster_required = cephx
     auth_service_required = cephx
     auth_client_required = cephx

* Copy Ceph keyring to ``/etc/kolla/config/glance/ceph.<ceph_glance_keyring>``

To configure multiple Ceph backends with Glance, which is useful
for multistore:

* Copy the Ceph configuration files into ``/etc/kolla/config/glance/`` using
  different names for each

  ``/etc/kolla/config/glance/ceph.conf``

  .. path /etc/kolla/config/glance/ceph.conf
  .. code-block:: ini

     [global]
     fsid = 1d89fec3-325a-4963-a950-c4afedd37fe3
     keyring = /etc/ceph/ceph.client.glance.keyring
     mon_initial_members = ceph-0
     mon_host = 192.168.0.56
     auth_cluster_required = cephx
     auth_service_required = cephx
     auth_client_required = cephx

  ``/etc/kolla/config/glance/rbd1.conf``

  .. path /etc/kolla/config/glance/rbd1.conf
  .. code-block:: ini

     [global]
     fsid = dbfea068-89ca-4d04-bba0-1b8a56c3abc8
     keyring = /etc/ceph/rbd1.client.glance.keyring
     mon_initial_members = ceph-0
     mon_host = 192.10.0.100
     auth_cluster_required = cephx
     auth_service_required = cephx
     auth_client_required = cephx

* Declare Ceph backends in ``globals.yml``

  .. code-block:: yaml

     glance_ceph_backends:
       - name: "rbd"
         type: "rbd"
         cluster: "ceph"
         enabled: "{{ glance_backend_ceph | bool }}"
       - name: "another-rbd"
         type: "rbd"
         cluster: "rbd1"
         enabled: "{{ glance_backend_ceph | bool }}"

* Copy Ceph keyring to ``/etc/kolla/config/glance/ceph.<ceph_glance_keyring>``
  and analogously to ``/etc/kolla/config/glance/rbd1.<ceph_glance_keyring>``

* For copy-on-write set following in ``/etc/kolla/config/glance.conf``:

  .. path /etc/kolla/config/glance.conf
  .. code-block:: ini

     [DEFAULT]
     show_image_direct_url = True

.. warning::

   ``show_image_direct_url`` can present a security risk if using more
   than just Ceph as Glance backend(s). Please see
   :glance-doc:`Glance show_image_direct_url <configuration/glance_api.html#DEFAULT.show_image_direct_url>`

Cinder
------

Ceph RBD can be used as a storage backend for Cinder volumes. Configuring
Cinder for Ceph includes following steps:

* When using external Ceph, there may be no nodes defined in the storage
  group.  This will cause Cinder and related services relying on this group to
  fail.  In this case, operator should add some nodes to the storage group,
  all the nodes where ``cinder-volume`` and ``cinder-backup`` will run:

  .. code-block:: ini

     [storage]
     control01

* Enable Cinder Ceph backend in ``globals.yml``:

  .. code-block:: yaml

     cinder_backend_ceph: "yes"

* Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

  * ``ceph_cinder_keyring`` (default: ``client.cinder.keyring``)
  * ``ceph_cinder_user`` (default: ``cinder``)
  * ``ceph_cinder_pool_name`` (default: ``volumes``)
  * ``ceph_cinder_backup_keyring``
    (default: ``client.cinder-backup.keyring``)
  * ``ceph_cinder_backup_user`` (default: ``cinder-backup``)
  * ``ceph_cinder_backup_pool_name`` (default: ``backups``)

* Copy Ceph configuration file to ``/etc/kolla/config/cinder/ceph.conf``

  Separate configuration options can be configured for
  cinder-volume and cinder-backup by adding ceph.conf files to
  ``/etc/kolla/config/cinder/cinder-volume`` and
  ``/etc/kolla/config/cinder/cinder-backup`` respectively. They
  will be merged with ``/etc/kolla/config/cinder/ceph.conf``.

* Copy Ceph keyring files to:

  * ``/etc/kolla/config/cinder/cinder-volume/ceph.<ceph_cinder_keyring>``
  * ``/etc/kolla/config/cinder/cinder-backup/ceph.<ceph_cinder_keyring>``
  * ``/etc/kolla/config/cinder/cinder-backup/ceph.
    <ceph_cinder_backup_keyring>``

.. note::

   ``cinder-backup`` requires two keyrings for accessing volumes
   and backup pool.

To configure ``multiple Ceph backends`` with Cinder, which is useful for
the use with availability zones:

* Copy their Ceph configuration files into ``/etc/kolla/config/cinder/`` using
  different names for each

  ``/etc/kolla/config/cinder/ceph.conf``

  .. path /etc/kolla/config/cinder/ceph.conf
  .. code-block:: ini

     [global]
     fsid = 1d89fec3-325a-4963-a950-c4afedd37fe3
     mon_initial_members = ceph-0
     mon_host = 192.168.0.56
     auth_cluster_required = cephx
     auth_service_required = cephx
     auth_client_required = cephx

  ``/etc/kolla/config/cinder/rbd2.conf``

  .. path /etc/kolla/config/cinder/rbd2.conf
  .. code-block:: ini

     [global]
     fsid = dbfea068-89ca-4d04-bba0-1b8a56c3abc8
     mon_initial_members = ceph-0
     mon_host = 192.10.0.100
     auth_cluster_required = cephx
     auth_service_required = cephx
     auth_client_required = cephx

* Declare Ceph backends in ``globals.yml``

  .. code-block:: yaml

     cinder_ceph_backends:
       - name: "rbd-1"
         cluster: "ceph"
         enabled: "{{ cinder_backend_ceph | bool }}"
       - name: "rbd-2"
         cluster: "rbd2"
         availability_zone: "az2"
         enabled: "{{ cinder_backend_ceph | bool }}"

* Copy Ceph keyring files for all Ceph backends:

  * ``/etc/kolla/config/cinder/cinder-volume/ceph.<ceph_cinder_keyring>``
  * ``/etc/kolla/config/cinder/cinder-backup/ceph.<ceph_cinder_keyring>``
  * ``/etc/kolla/config/cinder/cinder-backup/ceph.
    <ceph_cinder_backup_keyring>``
  * ``/etc/kolla/config/cinder/cinder-volume/rbd2.<ceph_cinder_keyring>``
  * ``/etc/kolla/config/cinder/cinder-backup/rbd2.<ceph_cinder_keyring>``
  * ``/etc/kolla/config/cinder/cinder-backup/rbd2.
    <ceph_cinder_backup_keyring>``

.. note::

   ``cinder-backup`` requires two keyrings for accessing volumes
   and backup pool.

Nova must also be configured to allow access to Cinder volumes:

* Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

  * ``ceph_cinder_keyring`` (default: ``client.cinder.keyring``)

* Copy Ceph keyring file(s) to:

  * ``/etc/kolla/config/nova/ceph.<ceph_cinder_keyring>``

To configure ``different Ceph backend`` for nova-compute host, which
is useful for the use with availability zones:

* Copy Ceph keyring file to:

  * ``/etc/kolla/config/nova/<hostname>/ceph.<ceph_cinder_keyring>``

If ``zun`` is enabled, and you wish to use cinder volumes with zun,
it must also be configured to allow access to Cinder volumes:

* Enable Cinder Ceph backend for Zun in ``globals.yml``:

  .. code-block:: yaml

     zun_configure_for_cinder_ceph: "yes"

* Copy Ceph configuration file to:

  * ``/etc/kolla/config/zun/zun-compute/ceph.conf``

* Copy Ceph keyring file(s) to:

  * ``/etc/kolla/config/zun/zun-compute/ceph.<ceph_cinder_keyring>``


Nova
----

Ceph RBD can be used as a storage backend for Nova instance ephemeral disks.
This avoids the requirement for local storage for instances on compute nodes.
It improves the performance of migration, since instances' ephemeral disks do
not need to be copied between hypervisors.

Configuring Nova for Ceph includes following steps:

* Enable Nova Ceph backend in ``globals.yml``:

  .. code-block:: yaml

     nova_backend_ceph: "yes"

* Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

  * ``ceph_nova_keyring`` (by default it's the same as
    ``ceph_cinder_keyring``)
  * ``ceph_nova_user`` (by default it's the same as ``ceph_cinder_user``)
  * ``ceph_nova_pool_name`` (default: ``vms``)

* Copy Ceph configuration file to ``/etc/kolla/config/nova/ceph.conf``
* Copy Ceph keyring file(s) to:

  * ``/etc/kolla/config/nova/ceph.<ceph_nova_keyring>``

  .. note::

     If you are using a Ceph deployment tool that generates separate Ceph
     keys for Cinder and Nova, you will need to override
     ``ceph_nova_keyring`` and ``ceph_nova_user`` to match.

To configure ``different Ceph backend`` for nova-compute host, which
is useful for the use with availability zones:

* Copy Ceph configuration file to ``/etc/kolla/config/nova/
  <hostname>/ceph.conf``
* Copy Ceph keyring file(s) to:

  * ``/etc/kolla/config/nova/<hostname>/ceph.<ceph_nova_keyring>``

Gnocchi
-------

Ceph object storage can be used as a storage backend for Gnocchi metrics.
Configuring Gnocchi for Ceph includes following steps:

* Enable Gnocchi Ceph backend in ``globals.yml``:

  .. code-block:: yaml

     gnocchi_backend_storage: "ceph"

* Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

  * ``ceph_gnocchi_keyring``
    (default: ``client.gnocchi.keyring``)
  * ``ceph_gnocchi_user`` (default: ``gnocchi``)
  * ``ceph_gnocchi_pool_name`` (default: ``gnocchi``)
  * ``ceph_gnocchi_conf``
    (default: ``ceph.conf``)

* Copy Ceph configuration file to
  ``/etc/kolla/config/gnocchi/<ceph_gnocchi_conf>``
* Copy Ceph keyring to
  ``/etc/kolla/config/gnocchi/ceph.<ceph_gnocchi_keyring>``

Manila
------

CephFS can be used as a storage backend for Manila shares. Configuring Manila
for Ceph includes following steps:

* Enable Manila Ceph backend in ``globals.yml``:

  .. code-block:: yaml

     enable_manila_backend_cephfs_native: "yes"

* Configure Ceph authentication details in ``/etc/kolla/globals.yml``:

  * ``ceph_manila_keyring`` (default: ``client.manila.keyring``)
  * ``ceph_manila_user`` (default: ``manila``)

  .. note::

     Required Ceph identity caps for manila user are documented in
     :manila-doc:`CephFS Native driver <admin/cephfs_driver.html#authorizing-the-driver-to-communicate-with-ceph>`.

* Copy Ceph configuration file to ``/etc/kolla/config/manila/ceph.conf``
* Copy Ceph keyring to ``/etc/kolla/config/manila/ceph.<ceph_manila_keyring>``

To configure ``multiple Ceph backends`` with Manila, which is useful for
the use with availability zones:

* Copy their Ceph configuration files into ``/etc/kolla/config/manila/`` using
  different names for each

  ``/etc/kolla/config/manila/ceph.conf``

  .. path /etc/kolla/config/manila/ceph.conf
  .. code-block:: ini

     [global]
     fsid = 1d89fec3-325a-4963-a950-c4afedd37fe3
     mon_initial_members = ceph-0
     mon_host = 192.168.0.56
     auth_cluster_required = cephx
     auth_service_required = cephx
     auth_client_required = cephx

  ``/etc/kolla/config/manila/rbd2.conf``

  .. path /etc/kolla/config/manila/rbd2.conf
  .. code-block:: ini

     [global]
     fsid = dbfea068-89ca-4d04-bba0-1b8a56c3abc8
     mon_initial_members = ceph-0
     mon_host = 192.10.0.100
     auth_cluster_required = cephx
     auth_service_required = cephx
     auth_client_required = cephx

* Declare Ceph backends in ``globals.yml``

  .. code-block:: yaml

     manila_ceph_backends:
       - name: "cephfsnative1"
         share_name: "CEPHFS1"
         driver: "cephfsnative"
         cluster: "ceph"
         enabled: "{{ enable_manila_backend_cephfs_native | bool }}"
         protocols:
           - "CEPHFS"
       - name: "cephfsnative2"
         share_name: "CEPHFS2"
         driver: "cephfsnative"
         cluster: "rbd2"
         enabled: "{{ enable_manila_backend_cephfs_native | bool }}"
         protocols:
           - "CEPHFS"
       - name: "cephfsnfs1"
         share_name: "CEPHFSNFS1"
         driver: "cephfsnfs"
         cluster: "ceph1"
         enabled: "{{ enable_manila_backend_cephfs_nfs | bool }}"
         protocols:
           - "NFS"
           - "CIFS"
       - name: "cephfsnfs2"
         share_name: "CEPHFSNFS2"
         driver: "cephfsnfs"
         cluster: "rbd2"
         enabled: "{{ enable_manila_backend_cephfs_nfs | bool }}"
         protocols:
           - "NFS"
           - "CIFS"

* Copy Ceph keyring files for all Ceph backends:

  * ``/etc/kolla/config/manila/manila-share/ceph.<ceph_manila_keyring>``
  * ``/etc/kolla/config/manila/manila-share/rbd2.<ceph_manila_keyring>``

* If using multiple filesystems (Ceph Pacific+), set
  ``manila_cephfs_filesystem_name`` in ``/etc/kolla/globals.yml`` to the
  name of the Ceph filesystem Manila should use.
  By default, Manila will use the first filesystem returned by
  the ``ceph fs volume ls`` command.

* Setup Manila in the usual way

For more details on the rest of the Manila setup, such as creating the share
type ``default_share_type``, please see :doc:`Manila in Kolla <manila-guide>`.

For more details on the CephFS Native driver, please see
:manila-doc:`CephFS Native driver <admin/cephfs_driver.html>`.

RadosGW
-------

As of the Xena 13.0.0 release, Kolla Ansible supports integration with Ceph
RadosGW. This includes:

* Registration of Swift-compatible endpoints in Keystone
* Load balancing across RadosGW API servers using HAProxy

See the `Ceph documentation
<https://docs.ceph.com/en/latest/radosgw/keystone/>`__ for further information,
including changes that must be applied to the Ceph cluster configuration.

Enable Ceph RadosGW integration:

.. code-block:: yaml

   enable_ceph_rgw: true

Keystone integration
====================

A Keystone user and endpoints are registered by default, however this may be
avoided by setting ``enable_ceph_rgw_keystone`` to ``false``. If registration
is enabled, the username is defined via ``ceph_rgw_keystone_user``, and this
defaults to ``ceph_rgw``. The hostnames used by the endpoints default to
``ceph_rgw_external_fqdn`` and ``ceph_rgw_internal_fqdn`` for the public and
internal endpoints respectively. These default to ``kolla_external_fqdn`` and
``kolla_internal_fqdn`` respectively. The port used by the endpoints is defined
via ``ceph_rgw_port``, and defaults to 6780.

By default RadosGW supports both Swift and S3 API, and it is not completely
compatible with Swift API. The option ``ceph_rgw_swift_compatibility`` can
enable/disable complete RadosGW compatibility with Swift API.  This should
match the configuration used by Ceph RadosGW. After changing the value, run
the ``kolla-ansible deploy`` command to enable.

By default, the RadosGW endpoint URL does not include the project (account) ID.
This prevents cross-project and public object access. This can be resolved by
setting ``ceph_rgw_swift_account_in_url`` to ``true``. This should match the
``rgw_swift_account_in_url`` configuration option in Ceph RadosGW.

Load balancing
==============

.. warning::

   Users of Ceph RadosGW can generate very high volumes of traffic. It is
   advisable to use a separate load balancer for RadosGW for anything other
   than small or lightly utilised RadosGW deployments, however this is
   currently out of scope for Kolla Ansible.

Load balancing is enabled by default, however this may be avoided by setting
``enable_ceph_rgw_loadbalancer`` to ``false``. If using load balancing, the
RadosGW hosts and ports must be configured. Each item should contain
``host`` and ``port`` keys. The ``ip`` and ``port`` keys are optional. If
``ip`` is not specified, the ``host`` values should be resolvable from the host
running HAProxy. If the ``port`` is not specified, the default HTTP (80) or
HTTPS (443) port will be used. For example:

.. code-block:: yaml

   ceph_rgw_hosts:
     - host: rgw-host-1
     - host: rgw-host-2
       ip: 10.0.0.42
       port: 8080

The HAProxy frontend port is defined via ``ceph_rgw_port``, and defaults to
6780.

Cephadm and Ceph Client Version
===============================
When configuring Zun with Cinder volumes, kolla-ansible installs some
Ceph client packages on zun-compute hosts. You can set the version
of the Ceph packages installed by,

* Configuring Ceph version details in ``/etc/kolla/globals.yml``:

  * ``ceph_version`` (default: ``pacific``)
