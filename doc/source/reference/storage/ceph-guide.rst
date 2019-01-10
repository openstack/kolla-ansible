.. _ceph-guide:

===============================
Ceph - Software Defined Storage
===============================

.. note::
   The out-of-the-box Ceph deployment requires 3 hosts with at least one block
   device on each host that can be dedicated for sole use by Ceph.

   However, with tweaks to the Ceph cluster you can deploy a **healthy** cluster
   with a single host and a single block device.

Requirements
------------

* A minimum of 3 hosts for a vanilla deploy
* A minimum of 1 block device per host

Preparation
-----------

To prepare a disk for use as a
`Ceph OSD <http://docs.ceph.com/docs/master/man/8/ceph-osd/>`_ you must add a
special partition label to the disk. This partition label is how Kolla detects
the disks to format and bootstrap. Any disk with a matching partition label
will be reformatted so use caution.

Filestore
~~~~~~~~~

.. note::

   From Rocky release - kolla-ansible by default creates Bluestore OSDs.
   Please see Configuration section to change that behaviour.

To prepare a filestore OSD as a storage drive, execute the following
operations:

.. warning::

   ALL DATA ON $DISK will be LOST! Where $DISK is /dev/sdb or something similar.

.. code-block:: console

   parted $DISK -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP 1 -1

The following shows an example of using parted to configure ``/dev/sdb`` for
usage with Kolla.

.. code-block:: console

   parted /dev/sdb -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP 1 -1
   parted /dev/sdb print
   Model: VMware, VMware Virtual S (scsi)
   Disk /dev/sdb: 10.7GB
   Sector size (logical/physical): 512B/512B
   Partition Table: gpt
   Number  Start   End     Size    File system  Name                      Flags
        1      1049kB  10.7GB  10.7GB               KOLLA_CEPH_OSD_BOOTSTRAP

Bluestore
~~~~~~~~~

To prepare a bluestore OSD partition, execute the following operations:

.. code-block:: console

   parted $DISK -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_BS 1 -1

If only one device is offered, Kolla Ceph will create the bluestore OSD on the
device. Kolla Ceph will create two partitions for OSD and block separately.

If more than one devices are offered for one bluestore OSD, Kolla Ceph will
create partitions for block, block.wal and block.db according to the partition
labels.

To prepare a bluestore OSD block partition, execute the following operations:

.. code-block:: console

   parted $DISK -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_BS_FOO_B 1 -1

To prepare a bluestore OSD block.wal partition, execute the following
operations:

.. code-block:: console

   parted $DISK -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_BS_FOO_W 1 -1

To prepare a bluestore OSD block.db partition, execute the following
operations:

.. code-block:: console

   parted $DISK -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_BS_FOO_D 1 -1

Kolla Ceph will handle the bluestore OSD according to the above up to four
partition labels. In Ceph bluestore OSD, the block.wal and block.db partitions
are not mandatory.

.. note::

   In the case there are more than one devices in one bluestore OSD and there
   are more than one bluestore OSD in one node, it is required to use suffixes
   (``_42``, ``_FOO``, ``_FOO42``, ..). Kolla Ceph will gather all the
   partition labels and deploy bluestore OSD on top of the devices which have
   the same suffix in the partition label.


Using an external journal drive
-------------------------------

.. note::

   The section is only meaningful for Ceph filestore OSD.

The steps documented above created a journal partition of 5 GByte
and a data partition with the remaining storage capacity on the same tagged
drive.

It is a common practice to place the journal of an OSD on a separate
journal drive. This section documents how to use an external journal drive.

Prepare the storage drive in the same way as documented above:

.. warning::

   ALL DATA ON $DISK will be LOST! Where $DISK is /dev/sdb or something similar.

.. code-block:: console

   parted $DISK -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_FOO 1 -1

To prepare the journal external drive execute the following command:

.. code-block:: console

   parted $DISK -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_FOO_J 1 -1

.. note::

   Use different suffixes (``_42``, ``_FOO``, ``_FOO42``, ..) to use different external
   journal drives for different storage drives. One external journal drive can only
   be used for one storage drive.

.. note::

   The partition labels ``KOLLA_CEPH_OSD_BOOTSTRAP`` and ``KOLLA_CEPH_OSD_BOOTSTRAP_J``
   are not working when using external journal drives. It is required to use
   suffixes (``_42``, ``_FOO``, ``_FOO42``, ..). If you want to setup only one
   storage drive with one external journal drive it is also necessary to use a suffix.


Configuration
-------------

Edit the ``[storage]`` group in the inventory which contains the hostname
of the hosts that have the block devices you have prepped as shown above.

.. code-block:: ini

   [storage]
   controller
   compute1

Enable Ceph in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_ceph: "yes"

RadosGW is optional, enable it in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_ceph_rgw: "yes"

You can enable RadosGW to be registered as Swift in Keystone catalog:

.. code-block:: yaml

   enable_ceph_rgw_keystone: "yes"

.. note::

    By default RadosGW supports both Swift and S3 API, and it is not
    completely compatible with Swift API. The option `ceph_rgw_compatibility`
    in ``ansible/group_vars/all.yml`` can enable/disable the RadosGW
    compatibility with Swift API completely. After changing the value, run the
    "reconfigure“ command to enable.

Configure the Ceph store type in ``ansible/group_vars/all.yml``, the default
value is ``bluestore`` in Rocky:

.. code-block:: yaml

   ceph_osd_store_type: "bluestore"

.. note::

    Regarding number of placement groups (PGs)

    Kolla sets very conservative values for the number of PGs per pool
    (`ceph_pool_pg_num` and `ceph_pool_pgp_num`). This is in order to ensure
    the majority of users will be able to deploy Ceph out of the box. It is
    *highly* recommended to consult the official Ceph documentation regarding
    these values before running Ceph in any kind of production scenario.

RGW requires a healthy cluster in order to be successfully deployed. On initial
start up, RGW will create several pools. The first pool should be in an
operational state to proceed with the second one, and so on. So, in the case of
an **all-in-one** deployment, it is necessary to change the default number of
copies for the pools before deployment. Modify the file
``/etc/kolla/config/ceph.conf`` and add the contents:

.. path /etc/kolla/config/ceph.conf
.. code-block:: ini

   [global]
   osd pool default size = 1
   osd pool default min size = 1

To build a high performance and secure Ceph Storage Cluster, the Ceph community
recommend the use of two separate networks: public network and cluster network.
Edit the ``/etc/kolla/globals.yml`` and configure the ``cluster_interface``:

.. path /etc/kolla/globals.yml
.. code-block:: yaml

   cluster_interface: "eth2"

For more details, see `NETWORK CONFIGURATION REFERENCE
<http://docs.ceph.com/docs/master/rados/configuration/network-config-ref/#ceph-networks>`_
of Ceph Documentation.

Deployment
----------

Finally deploy the Ceph-enabled OpenStack:

.. code-block:: console

   kolla-ansible deploy -i path/to/inventory

.. note::

   Kolla Ceph supports mixed Ceph OSD deployment, i.e. some Ceph OSDs are
   bluestore, the others are filestore. The ``ceph_osd_store_type`` of each
   Ceph OSD can be configured under ``[storage]`` in the multinode inventory
   file. The Ceph OSD store type is unique in one storage node. For example:

.. code-block:: ini

   [storage]
   storage_node1_hostname ceph_osd_store_type=bluestore
   storage_node2_hostname ceph_osd_store_type=bluestore
   storage_node3_hostname ceph_osd_store_type=filestore
   storage_node4_hostname ceph_osd_store_type=filestore

Using Cache Tiering
-------------------

An optional `cache tiering <http://docs.ceph.com/docs/jewel/rados/operations/cache-tiering/>`_
can be deployed by formatting at least one cache device and enabling cache.
tiering in the globals.yml configuration file.

To prepare a filestore OSD as a cache device, execute the following
operations:

.. code-block:: console

   parted $DISK -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_CACHE_BOOTSTRAP 1 -1

.. note::

   To prepare a bluestore OSD as a cache device, change the partition name in
   the above command to "KOLLA_CEPH_OSD_CACHE_BOOTSTRAP_BS". The deployment of
   bluestore cache OSD is the same as bluestore OSD.

Enable the Ceph cache tier in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_ceph: "yes"
   ceph_enable_cache: "yes"
   # Valid options are [ forward, none, writeback ]
   ceph_cache_mode: "writeback"

After this run the playbooks as you normally would, for example:

.. code-block:: console

   kolla-ansible deploy -i path/to/inventory

Setting up an Erasure Coded Pool
--------------------------------

`Erasure code <http://docs.ceph.com/docs/jewel/rados/operations/erasure-code/>`_
is the new big thing from Ceph. Kolla has the ability to setup your Ceph pools
as erasure coded pools. Due to technical limitations with Ceph, using erasure
coded pools as OpenStack uses them requires a cache tier. Additionally, you
must make the choice to use an erasure coded pool or a replicated pool
(the default) when you initially deploy. You cannot change this without
completely removing the pool and recreating it.

To enable erasure coded pools add the following options to your
``/etc/kolla/globals.yml`` configuration file:

.. code-block:: yaml

   # A requirement for using the erasure-coded pools is you must setup a cache tier
   # Valid options are [ erasure, replicated ]
   ceph_pool_type: "erasure"
   # Optionally, you can change the profile
   #ceph_erasure_profile: "k=4 m=2 ruleset-failure-domain=host"

Managing Ceph
-------------

Check the Ceph status for more diagnostic information. The sample output below
indicates a healthy cluster:

.. code-block:: console

   docker exec ceph_mon ceph -s

   cluster:
     id:     f2ed6c00-c043-4e1c-81b6-07c512db26b1
     health: HEALTH_OK

   services:
     mon: 1 daemons, quorum 172.16.31.121
     mgr: poc12-01(active)
     osd: 4 osds: 4 up, 4 in; 5 remapped pgs

   data:
     pools:   4 pools, 512 pgs
     objects: 0 objects, 0 bytes
     usage:   432 MB used, 60963 MB / 61395 MB avail
     pgs:     512 active+clean

If Ceph is run in an **all-in-one** deployment or with less than three storage
nodes, further configuration is required. It is necessary to change the default
number of copies for the pool. The following example demonstrates how to change
the number of copies for the pool to 1:

.. code-block:: console

   docker exec ceph_mon ceph osd pool set rbd size 1

All the pools must be modified if Glance, Nova, and Cinder have been deployed.
An example of modifying the pools to have 2 copies:

.. code-block:: console

   for p in images vms volumes backups; do docker exec ceph_mon ceph osd pool set ${p} size 2; done

If using a cache tier, these changes must be made as well:

.. code-block:: console

   for p in images vms volumes backups; do docker exec ceph_mon ceph osd pool set ${p}-cache size 2; done

The default pool Ceph creates is named **rbd**. It is safe to remove this pool:

.. code-block:: console

   docker exec ceph_mon ceph osd pool delete rbd rbd --yes-i-really-really-mean-it

Troubleshooting
---------------

Deploy fails with 'Fetching Ceph keyrings ... No JSON object could be decoded'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If an initial deploy of Ceph fails, perhaps due to improper configuration or
similar, the cluster will be partially formed and will need to be reset for a
successful deploy.

In order to do this the operator should remove the `ceph_mon_config` volume
from each Ceph monitor node:

.. code-block:: console

   ansible -i ansible/inventory/multinode \
       -a 'docker volume rm ceph_mon_config' \
       ceph-mon

Simple 3 Node Example
---------------------

This example will show how to deploy Ceph in a very simple setup using 3
storage nodes. 2 of those nodes (kolla1 and kolla2) will also provide other
services like control, network, compute, and monitoring. The 3rd
(kolla3) node will only act as a storage node.

This example will only focus on the Ceph aspect of the deployment and assumes
that you can already deploy a fully functional environment using 2 nodes that
does not employ Ceph yet. So we will be adding to the existing multinode
inventory file you already have.

Each of the 3 nodes are assumed to have two disk, ``/dev/sda`` (40GB)
and ``/dev/sdb`` (10GB). Size is not all that important... but for now make
sure each sdb disk are of the same size and are at least 10GB. This example
will use a single disk (/dev/sdb) for both Ceph data and journal. It will not
implement caching.

Here is the top part of the multinode inventory file used in the example
environment before adding the 3rd node for Ceph:

.. code-block:: ini

   [control]
   # These hostname must be resolvable from your deployment host
   kolla1.ducourrier.com
   kolla2.ducourrier.com

   [network]
   kolla1.ducourrier.com
   kolla2.ducourrier.com

   [compute]
   kolla1.ducourrier.com
   kolla2.ducourrier.com

   [monitoring]
   kolla1.ducourrier.com
   kolla2.ducourrier.com

   [storage]
   kolla1.ducourrier.com
   kolla2.ducourrier.com

Configuration
~~~~~~~~~~~~~

To prepare the 2nd disk (/dev/sdb) of each nodes for use by Ceph you will need
to add a partition label to it as shown below:

.. code-block:: console

   parted /dev/sdb -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP 1 -1

Make sure to run this command on each of the 3 nodes or the deployment will
fail.

Next, edit the multinode inventory file and make sure the 3 nodes are listed
under ``[storage]``. In this example I will add kolla3.ducourrier.com to the
existing inventory file:

.. code-block:: ini

   [control]
   # These hostname must be resolvable from your deployment host
   kolla1.ducourrier.com
   kolla2.ducourrier.com

   [network]
   kolla1.ducourrier.com
   kolla2.ducourrier.com

   [compute]
   kolla1.ducourrier.com
   kolla2.ducourrier.com

   [monitoring]
   kolla1.ducourrier.com
   kolla2.ducourrier.com

   [storage]
   kolla1.ducourrier.com
   kolla2.ducourrier.com
   kolla3.ducourrier.com

It is now time to enable Ceph in the environment by editing the
``/etc/kolla/globals.yml`` file:

.. code-block:: yaml

   enable_ceph: "yes"
   enable_ceph_rgw: "yes"
   enable_cinder: "yes"
   glance_backend_file: "no"
   glance_backend_ceph: "yes"

Deployment
~~~~~~~~~~

Finally deploy the Ceph-enabled configuration:

.. code-block:: console

   kolla-ansible deploy -i path/to/inventory-file

