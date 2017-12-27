.. _cinder-guide-hnas:

========================================================
Hitachi NAS Platform iSCSI and NFS drives for OpenStack
========================================================

Overview
========
The Block Storage service provides persistent block storage resources that
Compute instances can consume. This includes secondary attached storage similar
to the Amazon Elastic Block Storage (EBS) offering. In addition, you can write
images to a Block Storage device for Compute to use as a bootable persistent
instance.

Requirements
------------
- Hitachi NAS Platform Models 3080, 3090, 4040, 4060, 4080, and 4100.

- HNAS/SMU software version is 12.2 or higher.

- HNAS configuration and management utilities to create a storage pool (span)
  and an EVS.

  -  GUI (SMU).

  -  SSC CLI.

- You must set an iSCSI domain to EVS

Supported shared file systems and operations
--------------------------------------------

The NFS and iSCSI drivers support these operations:

- Create, delete, attach, and detach volumes.

- Create, list, and delete volume snapshots.

- Create a volume from a snapshot.

- Copy an image to a volume.

- Copy a volume to an image.

- Clone a volume.

- Extend a volume.

- Get volume statistics.

- Manage and unmanage a volume.

- Manage and unmanage snapshots (HNAS NFS only).

Configuration example for Hitachi NAS Platform iSCSI and NFS
============================================================

iSCSI backend
-------------

Enable cinder hnas backend iscsi in ``/etc/kolla/globals.yml``

.. code-block:: console

    enable_cinder_backend_hnas_iscsi: "yes"

Create or modify the file ``/etc/kolla/config/cinder.conf`` and add the
contents:

.. code-block:: console

    [DEFAULT]
    enabled_backends = hnas-iscsi

    [hnas-iscsi]
    volume_driver = cinder.volume.drivers.hitachi.hnas_iscsi.HNASISCSIDriver
    volume_iscsi_backend = hnas_iscsi_backend
    hnas_iscsi_username = supervisor
    hnas_iscsi_password = supervisor
    hnas_iscsi_mgmt_ip0 = <hnas_ip>
    hnas_chap_enabled = True

    hnas_iscsi_svc0_volume_type = iscsi_gold
    hnas_iscsi_svc0_hdp = FS-Baremetal1
    hnas_iscsi_svc0_iscsi_ip = <svc0_ip>

NFS backend
-----------

Enable cinder hnas backend nfs in ``/etc/kolla/globals.yml``

.. code-block:: console

    enable_cinder_backend_hnas_nfs: "yes"

Create or modify the file ``/etc/kolla/config/cinder.conf`` and
add the contents:

.. code-block:: console

    [DEFAULT]
    enabled_backends = hnas-nfs

    [hnas-nfs]
    volume_driver = cinder.volume.drivers.hitachi.hnas_nfs.HNASNFSDriver
    volume_nfs_backend = hnas_nfs_backend
    hnas_nfs_username = supervisor
    hnas_nfs_password = supervisor
    hnas_nfs_mgmt_ip0 = <hnas_ip>
    hnas_chap_enabled = True

    hnas_nfs_svc0_volume_type = nfs_gold
    hnas_nfs_svc0_hdp = <svc0_ip>/<export_name>

Configuration on Kolla deployment
---------------------------------

Enable Shared File Systems service and HNAS driver in
``/etc/kolla/globals.yml``

.. code-block:: console

    enable_cinder: "yes"

Configuration on HNAS
---------------------

Create the data HNAS network in Kolla OpenStack:

List the available tenants:

.. code-block:: console

    $ openstack project list

Create a network to the given tenant (service), providing the tenant ID,
a name for the network, the name of the physical network over which the
virtual network is implemented, and the type of the physical mechanism by
which the virtual network is implemented:

.. code-block:: console

    $ neutron net-create --tenant-id <SERVICE_ID> hnas_network \
    --provider:physical_network=physnet2 --provider:network_type=flat

Create a subnet to the same tenant (service), the gateway IP of this subnet,
a name for the subnet, the network ID created before, and the CIDR of
subnet:

.. code-block:: console

    $ neutron subnet-create --tenant-id <SERVICE_ID> --gateway <GATEWAY> \
    --name hnas_subnet <NETWORK_ID> <SUBNET_CIDR>

Add the subnet interface to a router, providing the router ID and subnet
ID created before:

.. code-block:: console

    $ neutron router-interface-add <ROUTER_ID> <SUBNET_ID>

Create volume
=============

Create a non-bootable volume.

.. code-block:: console

    $ openstack volume create --size 1 my-volume

Verify Operation.

.. code-block:: console

    $ cinder show my-volume

    +--------------------------------+--------------------------------------+
    | Property                       | Value                                |
    +--------------------------------+--------------------------------------+
    | attachments                    | []                                   |
    | availability_zone              | nova                                 |
    | bootable                       | false                                |
    | consistencygroup_id            | None                                 |
    | created_at                     | 2017-01-17T19:02:45.000000           |
    | description                    | None                                 |
    | encrypted                      | False                                |
    | id                             | 4f5b8ae8-9781-411e-8ced-de616ae64cfd |
    | metadata                       | {}                                   |
    | migration_status               | None                                 |
    | multiattach                    | False                                |
    | name                           | my-volume                            |
    | os-vol-host-attr:host          | compute@hnas-iscsi#iscsi_gold        |
    | os-vol-mig-status-attr:migstat | None                                 |
    | os-vol-mig-status-attr:name_id | None                                 |
    | os-vol-tenant-attr:tenant_id   | 16def9176bc64bd283d419ac2651e299     |
    | replication_status             | disabled                             |
    | size                           | 1                                    |
    | snapshot_id                    | None                                 |
    | source_volid                   | None                                 |
    | status                         | available                            |
    | updated_at                     | 2017-01-17T19:02:46.000000           |
    | user_id                        | fb318b96929c41c6949360c4ccdbf8c0     |
    | volume_type                    | None                                 |
    +--------------------------------+--------------------------------------+

    $ nova volume-attach INSTANCE_ID VOLUME_ID auto

    +----------+--------------------------------------+
    | Property | Value                                |
    +----------+--------------------------------------+
    | device   | /dev/vdc                             |
    | id       | 4f5b8ae8-9781-411e-8ced-de616ae64cfd |
    | serverId | 3bf5e176-be05-4634-8cbd-e5fe491f5f9c |
    | volumeId | 4f5b8ae8-9781-411e-8ced-de616ae64cfd |
    +----------+--------------------------------------+

    $ openstack volume list

    +--------------------------------------+---------------+----------------+------+-------------------------------------------+
    | ID                                   | Display Name  | Status         | Size | Attached to                               |
    +--------------------------------------+---------------+----------------+------+-------------------------------------------+
    | 4f5b8ae8-9781-411e-8ced-de616ae64cfd | my-volume     | in-use         |    1 | Attached to private-instance on /dev/vdb  |
    +--------------------------------------+---------------+----------------+------+-------------------------------------------+

For more information about how to manage volumes, see the
`OpenStack User Guide
<http://docs.openstack.org/user-guide/index.html>`__.

For more information about how HNAS driver works, see
`Hitachi NAS Platform iSCSI and NFS drives for OpenStack
<http://docs.openstack.org/newton/config-reference/block-storage/drivers/hds-hnas-driver.html>`__.
