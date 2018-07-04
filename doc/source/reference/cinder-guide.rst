.. _cinder-guide:

===============
Cinder in Kolla
===============

Overview
~~~~~~~~

Cinder can be deployed using Kolla and supports the following storage
backends:

* ceph
* hnas_iscsi
* hnas_nfs
* iscsi
* lvm
* nfs

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

.. end

During development, it may be desirable to use file backed block storage. It
is possible to use a file and mount it as a block device via the loopback
system.

.. code-block:: console

   free_device=$(losetup -f)
   fallocate -l 20G /var/lib/cinder_data.img
   losetup $free_device /var/lib/cinder_data.img
   pvcreate $free_device
   vgcreate cinder-volumes $free_device

.. end

Enable the ``lvm`` backend in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_cinder_backend_lvm: "yes"

.. end

.. note::

   There are currently issues using the LVM backend in a multi-controller setup,
   see `_bug 1571211 <https://launchpad.net/bugs/1571211>`__ for more info.

NFS
~~~

To use the ``nfs`` backend, configure ``/etc/exports`` to contain the mount
where the volumes are to be stored:

.. code-block:: console

   /kolla_nfs 192.168.5.0/24(rw,sync,no_root_squash)

.. end

In this example, ``/kolla_nfs`` is the directory on the storage node which will
be ``nfs`` mounted, ``192.168.5.0/24`` is the storage network, and
``rw,sync,no_root_squash`` means make the share read-write, synchronous, and
prevent remote root users from having access to all files.

Then start ``nfsd``:

.. code-block:: console

   systemctl start nfs

.. end

On the deploy node, create ``/etc/kolla/config/nfs_shares`` with an entry for
each storage node:

.. code-block:: console

   storage01:/kolla_nfs
   storage02:/kolla_nfs

.. end

Finally, enable the ``nfs`` backend in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_cinder_backend_nfs: "yes"

.. end

Validation
~~~~~~~~~~

Create a volume as follows:

.. code-block:: console

   openstack volume create --size 1 steak_volume
   <bunch of stuff printed>

.. end

Verify it is available. If it says "error", then something went wrong during
LVM creation of the volume.

.. code-block:: console

   openstack volume list

   +--------------------------------------+--------------+-----------+------+-------------+
   | ID                                   | Display Name | Status    | Size | Attached to |
   +--------------------------------------+--------------+-----------+------+-------------+
   | 0069c17e-8a60-445a-b7f0-383a8b89f87e | steak_volume | available |    1 |             |
   +--------------------------------------+--------------+-----------+------+-------------+

.. end

Attach the volume to a server using:

.. code-block:: console

   openstack server add volume steak_server 0069c17e-8a60-445a-b7f0-383a8b89f87e

.. end

Check the console log to verify the disk addition:

.. code-block:: console

   openstack console log show steak_server

.. end

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

.. end

For Ubuntu and LVM2/iSCSI
-------------------------

``iscsd`` process uses configfs which is normally mounted at
``/sys/kernel/config`` to store discovered targets information, on centos/rhel
type of systems this special file system gets mounted automatically, which is
not the case on debian/ubuntu. Since ``iscsid`` container runs on every nova
compute node, the following steps must be completed on every Ubuntu server
targeted for nova compute role.

- Add configfs module to ``/etc/modules``
- Rebuild initramfs using: ``update-initramfs -u`` command
- Stop ``open-iscsi`` system service due to its conflicts
  with iscsid container.

  Ubuntu 16.04 (systemd):
  ``systemctl stop open-iscsi; systemctl stop iscsid``

- Make sure configfs gets mounted during a server boot up process. There are
  multiple ways to accomplish it, one example:

  .. code-block:: console

     mount -t configfs /etc/rc.local /sys/kernel/config

  .. end

Cinder backend with external iSCSI storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to use external storage system (like the ones from EMC or NetApp)
the following parameter must be specified in ``globals.yml``:

.. code-block:: yaml

   enable_cinder_backend_iscsi: "yes"

.. end

Also ``enable_cinder_backend_lvm`` should be set to ``no`` in this case.
