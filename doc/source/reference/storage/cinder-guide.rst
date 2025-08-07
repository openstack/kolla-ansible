.. _cinder-guide:

======================
Cinder - Block storage
======================

Overview
~~~~~~~~

Cinder can be deployed using Kolla and supports the following storage
backends:

* ceph
* iscsi
* lvm
* nfs

HA
~~

When using cinder-volume in an HA configuration (more than one host in
cinder-volume/storage group):

* Make sure that the driver you are using supports `Active/Active High
  Availability
  <https://docs.openstack.org/cinder/|OPENSTACK_RELEASE|/reference/support-matrix.html#operation_active_active_ha>`__
  configuration
* Add ``cinder_cluster_name: example_cluster_name`` to your ``globals.yml`` (or
  host_vars for advanced multi-cluster configuration)

.. note::

   In case of non-standard configurations (e.g. mixed HA and non-HA Cinder backends),
   you can skip the prechecks by setting ``cinder_cluster_skip_precheck`` to
   ``true``.

LVM
~~~

When using the ``lvm`` backend, a volume group should be created on each
storage node. This can either be a real physical volume or a loopback mounted
file for development.  Use ``pvcreate`` and ``vgcreate`` to create the volume
group.  For example with the devices ``/dev/sdb`` and ``/dev/sdc``:

.. code-block:: console

   <WARNING ALL DATA ON /dev/sdb and /dev/sdc will be LOST!>

   pvcreate /dev/sdb /dev/sdc
   vgcreate cinder-volumes /dev/sdb /dev/sdc

During development, it may be desirable to use file backed block storage. It
is possible to use a file and mount it as a block device via the loopback
system.

.. code-block:: console

   free_device=$(losetup -f)
   fallocate -l 20G /var/lib/cinder_data.img
   losetup $free_device /var/lib/cinder_data.img
   pvcreate $free_device
   vgcreate cinder-volumes $free_device

Enable the ``lvm`` backend in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_cinder_backend_lvm: "yes"

.. note::

   There are currently issues using the LVM backend in a multi-controller setup,
   see `_bug 1571211 <https://launchpad.net/bugs/1571211>`__ for more info.

NFS
~~~

To use the ``nfs`` backend, configure ``/etc/exports`` to contain the mount
where the volumes are to be stored:

.. code-block:: console

   /kolla_nfs 192.168.5.0/24(rw,sync,no_root_squash)

In this example, ``/kolla_nfs`` is the directory on the storage node which will
be ``nfs`` mounted, ``192.168.5.0/24`` is the storage network, and
``rw,sync,no_root_squash`` means make the share read-write, synchronous, and
prevent remote root users from having access to all files.

Then start ``nfsd``:

.. code-block:: console

   systemctl start nfs

On the deploy node, create ``/etc/kolla/config/nfs_shares`` with an entry for
each storage node:

.. code-block:: console

   storage01:/kolla_nfs
   storage02:/kolla_nfs

Finally, enable the ``nfs`` backend in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_cinder_backend_nfs: "yes"

Validation
~~~~~~~~~~

Create a volume as follows:

.. code-block:: console

   openstack volume create --size 1 steak_volume
   <bunch of stuff printed>

Verify it is available. If it says "error", then something went wrong during
LVM creation of the volume.

.. code-block:: console

   openstack volume list

   +--------------------------------------+--------------+-----------+------+-------------+
   | ID                                   | Display Name | Status    | Size | Attached to |
   +--------------------------------------+--------------+-----------+------+-------------+
   | 0069c17e-8a60-445a-b7f0-383a8b89f87e | steak_volume | available |    1 |             |
   +--------------------------------------+--------------+-----------+------+-------------+

Attach the volume to a server using:

.. code-block:: console

   openstack server add volume steak_server 0069c17e-8a60-445a-b7f0-383a8b89f87e

Check the console log to verify the disk addition:

.. code-block:: console

   openstack console log show steak_server

A ``/dev/vdb`` should appear in the console log, at least when booting cirros.
If the disk stays in the available state, something went wrong during the
iSCSI mounting of the volume to the guest VM.

Cinder LVM2 backend with iSCSI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As of Newton-1 milestone, Kolla supports LVM2 as cinder backend. It is
accomplished by introducing two new containers ``tgtd`` and ``iscsid``.
``tgtd`` container serves as a bridge between cinder-volume process and a
server hosting Logical Volume Groups (LVG). ``iscsid`` container serves as
a bridge between nova-compute process and the server hosting LVG.

In order to use Cinder's LVM backend, a LVG named ``cinder-volumes`` should
exist on the server and following parameter must be specified in
``globals.yml``:

.. code-block:: yaml

   enable_cinder_backend_lvm: "yes"

For Ubuntu and LVM2/iSCSI
-------------------------

``iscsd`` process uses configfs which is normally mounted at
``/sys/kernel/config`` to store discovered targets information, on centos/rhel
type of systems this special file system gets mounted automatically, which is
not the case on debian/ubuntu. Since ``iscsid`` container runs on every nova
compute node, the following steps must be completed on every Ubuntu server
targeted for nova compute role.

* Add configfs module to ``/etc/modules``
* Rebuild initramfs using: ``update-initramfs -u`` command
* Stop ``open-iscsi`` system service due to its conflicts
  with iscsid container.

  Ubuntu 16.04 (systemd):
  ``systemctl stop open-iscsi; systemctl stop iscsid``

* Make sure configfs gets mounted during a server boot up process. There are
  multiple ways to accomplish it, one example:

  .. code-block:: console

     mount -t configfs /etc/rc.local /sys/kernel/config

  .. note::

     There is currently an issue with the folder /sys/kernel/config as it is
     either empty or does not exist in several operating systems,
     see `_bug 1631072 <https://bugs.launchpad.net/kolla/+bug/1631072>`__ for more info

Cinder backend with external iSCSI storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to use external storage system (like the ones from EMC or NetApp)
the following parameter must be specified in ``globals.yml``:

.. code-block:: yaml

   enable_cinder_backend_iscsi: "yes"

Also ``enable_cinder_backend_lvm`` should be set to ``no`` in this case.

Skip Cinder prechecks for Custom backends
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to use custom storage backends which currently not yet implemented
in Kolla, the following parameter must be specified in ``globals.yml``:

.. code-block:: yaml

   skip_cinder_backend_check: True

All configuration for custom NFS backend should be performed
via ``cinder.conf`` in config overrides directory.

Cinder-Backup with S3 Backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configuring Cinder-Backup for S3 includes the following steps:

#. Enable Cinder-Backup S3 backend in ``globals.yml``:

.. code-block:: yaml

   cinder_backup_driver: "s3"

#. Configure S3 connection details in ``/etc/kolla/globals.yml``:

   * ``cinder_backup_s3_url`` (example: ``http://127.0.0.1:9000``)
   * ``cinder_backup_s3_access_key`` (example: ``minio``)
   * ``cinder_backup_s3_bucket`` (example: ``cinder``)
   * ``cinder_backup_s3_secret_key`` (example: ``admin``)

#. If you wish to use a single S3 backend for all supported services,
use the following variables:

   * ``s3_url``
   * ``s3_access_key``
   * ``s3_glance_bucket``
   * ``s3_secret_key``

   All Cinder-Backup S3 configurations use these options as default values.

Customizing backend names in cinder.conf
----------------------------------------

.. note::

   This is an advanced configuration option. You cannot change these variables
   if you already have volumes that use the old name without additional steps.
   Sensible defaults exist out of the box.

The following variables are available to customise the default backend name
that appears in cinder.conf:

.. list-table:: Variables to customize backend name
   :widths: 50 25 25
   :header-rows: 1

   * - Driver
     - Variable
     - Default value
   * - Ceph
     - cinder_backend_ceph_name
     - rbd-1
   * - Logical Volume Manager (LVM)
     - cinder_backend_lvm_name
     - lvm-1
   * - Network File System (NFS)
     - cinder_backend_nfs_name
     - nfs-1
   * - Quobyte Storage for OpenStack
     - cinder_backend_quobyte_name
     - QuobyteHD
   * - Pure Storage FlashArray for OpenStack (iSCSI)
     - cinder_backend_pure_iscsi_name
     - Pure-FlashArray-iscsi
   * - Pure Storage FlashArray for OpenStack
     - cinder_backend_pure_fc_name
     - Pure-FlashArray-fc
   * - Pure Storage FlashArray for OpenStack
     - cinder_backend_pure_roce_name
     - Pure-FlashArray-roce
   * - Pure Storage FlashArray for OpenStack
     - cinder_backend_pure_nvme_tcp_name
     - Pure-FlashArray-nvme-tcp
   * - Lightbits Labs storage backend
     - cinder_backend_lightbits_name
     - Lightbits-NVMe-TCP

These are the names you use when
`configuring <https://docs.openstack.org/cinder/latest/admin/multi-backend.html#volume-type>`_
``volume_backend_name`` on cinder volume types. It can sometimes be
useful to provide a more descriptive name.
