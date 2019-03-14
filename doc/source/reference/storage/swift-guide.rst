.. _swift-guide:

=============================
Swift- Object storage service
=============================

Overview
~~~~~~~~

Kolla can deploy a full working Swift setup in either a **all-in-one** or
**multinode** setup.

Networking
~~~~~~~~~~

The following networks are used by Swift:

External API network (``kolla_external_vip_interface``)
  This network is used by users to access the Swift public API.
Internal API network (``api_interface``)
  This network is used by users to access the Swift internal API. It is also
  used by HAProxy to access the Swift proxy servers.
Swift Storage network (``swift_storage_interface``)
  This network is used by the Swift proxy server to access the account,
  container and object servers. Defaults to ``storage_interface``.
Swift replication network (``swift_replication_network``)
  This network is used for Swift storage replication traffic.
  This is optional as the default configuration uses
  the ``swift_storage_interface`` for replication traffic.

Disks with a partition table (recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Swift requires block devices to be available for storage. To prepare a disk
for use as a Swift storage device, a special partition name and filesystem
label need to be added.

The following should be done on each storage node, the example is shown
for three disks:

.. warning::

   ALL DATA ON DISK will be LOST!

.. code-block:: console

   index=0
   for d in sdc sdd sde; do
       parted /dev/${d} -s -- mklabel gpt mkpart KOLLA_SWIFT_DATA 1 -1
       sudo mkfs.xfs -f -L d${index} /dev/${d}1
       (( index++ ))
   done

For evaluation, loopback devices can be used in lieu of real disks:

.. code-block:: console

   index=0
   for d in sdc sdd sde; do
       free_device=$(losetup -f)
       fallocate -l 1G /tmp/$d
       losetup $free_device /tmp/$d
       parted $free_device -s -- mklabel gpt mkpart KOLLA_SWIFT_DATA 1 -1
       sudo mkfs.xfs -f -L d${index} ${free_device}p1
       (( index++ ))
   done

Disks without a partition table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla also supports unpartitioned disk (filesystem on ``/dev/sdc`` instead of
``/dev/sdc1``) detection purely based on filesystem label. This is generally
not a recommended practice but can be helpful for Kolla to take over Swift
deployment already using disk like this.

Given hard disks with labels swd1, swd2, swd3, use the following settings in
``ansible/roles/swift/defaults/main.yml``.

.. code-block:: yaml

   swift_devices_match_mode: "prefix"
   swift_devices_name: "swd"

Rings
~~~~~

Before running Swift we need to generate **rings**, which are binary compressed
files that at a high level let the various Swift services know where data is in
the cluster. We hope to automate this process in a future release.

The following example commands should be run from the ``operator`` node to
generate rings for a demo setup. The commands work with **disks with partition
table** example listed above. Please modify accordingly if your setup is
different.

If using a separate replication network it is necessary to add the replication
network IP addresses to the rings. See the `Swift documentation
<https://docs.openstack.org/swift/latest/replication_network.html#dedicated-replication-network>`__
for details on how to do that.

Prepare for Rings generating
----------------------------

To prepare for Swift Rings generating, run the following commands to initialize
the environment variable and create ``/etc/kolla/config/swift`` directory:

.. code-block:: console

   STORAGE_NODES=(192.168.0.2 192.168.0.3 192.168.0.4)
   KOLLA_SWIFT_BASE_IMAGE="kolla/oraclelinux-source-swift-base:4.0.0"
   mkdir -p /etc/kolla/config/swift

Generate Object Ring
--------------------

To generate Swift object ring, run the following commands:

.. code-block:: console

   docker run \
     --rm \
     -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
     $KOLLA_SWIFT_BASE_IMAGE \
     swift-ring-builder \
       /etc/kolla/config/swift/object.builder create 10 3 1

   for node in ${STORAGE_NODES[@]}; do
       for i in {0..2}; do
         docker run \
           --rm \
           -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
           $KOLLA_SWIFT_BASE_IMAGE \
           swift-ring-builder \
             /etc/kolla/config/swift/object.builder add r1z1-${node}:6000/d${i} 1;
       done
   done

Generate Account Ring
---------------------

To generate Swift account ring, run the following commands:

.. code-block:: console

   docker run \
     --rm \
     -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
     $KOLLA_SWIFT_BASE_IMAGE \
     swift-ring-builder \
       /etc/kolla/config/swift/account.builder create 10 3 1

   for node in ${STORAGE_NODES[@]}; do
       for i in {0..2}; do
         docker run \
           --rm \
           -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
           $KOLLA_SWIFT_BASE_IMAGE \
           swift-ring-builder \
             /etc/kolla/config/swift/account.builder add r1z1-${node}:6001/d${i} 1;
       done
   done

Generate Container Ring
-----------------------

To generate Swift container ring, run the following commands:

.. code-block:: console

   docker run \
     --rm \
     -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
     $KOLLA_SWIFT_BASE_IMAGE \
     swift-ring-builder \
       /etc/kolla/config/swift/container.builder create 10 3 1

   for node in ${STORAGE_NODES[@]}; do
       for i in {0..2}; do
         docker run \
           --rm \
           -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
           $KOLLA_SWIFT_BASE_IMAGE \
           swift-ring-builder \
             /etc/kolla/config/swift/container.builder add r1z1-${node}:6002/d${i} 1;
       done
   done

.. end

Rebalance
---------

To rebalance the ring files:

.. code-block:: console

   for ring in object account container; do
     docker run \
       --rm \
       -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
       $KOLLA_SWIFT_BASE_IMAGE \
       swift-ring-builder \
         /etc/kolla/config/swift/${ring}.builder rebalance;
   done

For more information, see `the Swift documentation
<https://docs.openstack.org/swift/latest/install/initial-rings.html>`__.

Deploying
~~~~~~~~~

Enable Swift in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_swift : "yes"

Once the rings are in place, deploying Swift is the same as any other Kolla
Ansible service:

.. code-block:: console

   # kolla-ansible deploy -i <path/to/inventory-file>

Verification
~~~~~~~~~~~~

A very basic smoke test:

.. code-block:: console

   $ openstack container create mycontainer

   +---------------------------------------+--------------+------------------------------------+
   | account                               | container    | x-trans-id                         |
   +---------------------------------------+--------------+------------------------------------+
   | AUTH_7b938156dba44de7891f311c751f91d8 | mycontainer  | txb7f05fa81f244117ac1b7-005a0e7803 |
   +---------------------------------------+--------------+------------------------------------+

   $ openstack object create mycontainer README.rst

   +---------------+--------------+----------------------------------+
   | object        | container    | etag                             |
   +---------------+--------------+----------------------------------+
   | README.rst    | mycontainer  | 2634ecee0b9a52ba403a503cc7d8e988 |
   +---------------+--------------+----------------------------------+

   $ openstack container show mycontainer

   +--------------+---------------------------------------+
   | Field        | Value                                 |
   +--------------+---------------------------------------+
   | account      | AUTH_7b938156dba44de7891f311c751f91d8 |
   | bytes_used   | 6684                                  |
   | container    | mycontainer                           |
   | object_count | 1                                     |
   +--------------+---------------------------------------+

   $ openstack object store account show

   +------------+---------------------------------------+
   | Field      | Value                                 |
   +------------+---------------------------------------+
   | Account    | AUTH_7b938156dba44de7891f311c751f91d8 |
   | Bytes      | 6684                                  |
   | Containers | 1                                     |
   | Objects    | 1                                     |
   +------------+---------------------------------------+
