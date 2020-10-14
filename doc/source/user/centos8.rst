========
CentOS 8
========

This section covers use of Kolla Ansible on CentOS 8 in the Train release. From
the 9.1.0 release, Kolla Ansible supports both CentOS 7 and 8.

Scope
-----

We must consider the OS distribution and version running on the host, and in
the containers. Kolla Ansible does not support mixing different OS
distributions between the host and containers, nor does it support mixing
different major OS versions between the host and containers. The following
combinations are therefore supported:

* Host: CentOS 7, containers: CentOS 7
* Host: CentOS 8, containers: CentOS 8

Upgrade path
------------

The Train release is the last release to support CentOS 7, and the first to
support CentOS 8. CentOS 7 users wishing to upgrade beyond Train must therefore
migrate to CentOS 8. The upgrade path looks like this:

* Stein & earlier (CentOS 7)
* Train (CentOS 7)
* Train (CentOS 8)
* Ussuri & later (CentOS 8)

Feature removal
---------------

Note that the following features available on CentOS 7 are not available on
CentOS 8:

* integrated Ceph deployment. External Ceph integration is still supported.
* SCSI target daemon has been dropped in favour of LIO.
  ``cinder_target_helper`` is now ``lio`` by default on CentOS 8.

Container images
----------------

For details on how to build images for CentOS 8, see the :kolla-doc:`Kolla
image building guide <admin/image-building.html#building-kolla-images>`. Note
that for the Train release only, Kolla Ansible applies a ``-centos8`` suffix
(configured via ``openstack_tag_suffix``) to image tags by default on CentOS 8
hosts. The default tag on CentOS 8 hosts is therefore ``train-centos8``. This
is to differentiate CentOS 7 and CentOS 8 container images.

Migrating from CentOS 7 to CentOS 8
-----------------------------------

This section describes how to migrate an existing deployment from CentOS 7 to
CentOS 8.

There is no supported upgrade path from CentOS 7 to CentOS 8. Since we want to
use the same major versions of CentOS in the host and containers, the hosts
must be reinstalled with CentOS 8 before CentOS 8 containers are deployed.
Where possible, this should be done in batches to avoid downtime. The high
level workflow is:

* deploy or upgrade to the Train release onto CentOS 7 hosts
* upgrade services to ensure compatibility with those available in CentOS 8
* migrate hosts to CentOS 8 in batches

Note that in a multi-node system it is possible to have a mix of CentOS 7 and
CentOS 8 hosts while the migration takes place.

Service compatibility
~~~~~~~~~~~~~~~~~~~~~

This section describes how to ensure the services running on CentOS 7 hosts are
compatible with those that will be deployed on CentOS 8 hosts.

RabbitMQ
########

CentOS 7 by default uses RabbitMQ 3.7.10. CentOS 8 supports only RabbitMQ
3.7.24+. It is therefore necessary to upgrade RabbitMQ containers on CentOS 7
hosts to be compatible with those on CentOS 8 hosts. This can be done by adding
the following in ``globals.yml``:

.. code-block:: yaml

   rabbitmq_use_3_7_24_on_centos7: true

Now upgrade RabbitMQ:

.. code-block:: console

   kolla-ansible -i <inventory> upgrade -t rabbitmq

Elasticsearch & Kibana
######################

CentOS 7 by default uses Elasticsearch and Kibana 5.x. CentOS 8 supports only
6.x. It is therefore necessary to upgrade Elasticsearch and Kibana containers
on CentOS 7 hosts to be compatible with those on CentOS 8 hosts. This can be
done by adding the following in ``globals.yml``:

.. code-block:: yaml

   elasticsearch_use_v6: true
   kibana_use_v6: true

Now upgrade Elasticsearch & Kibana:

.. code-block:: console

   kolla-ansible -i <inventory> upgrade -t elasticsearch,kibana

Batched migration
~~~~~~~~~~~~~~~~~

This section describes how to perform a batched migration of hosts from CentOS
7 to CentOS 8.

It is recommended to migrate hosts in the following order:

* controllers
* compute nodes

Within each of the above groups, hosts should be migrated in batches of a
suitable size. The batch size should be chosen taking into consideration
availability and capacity constraints.  Testing should be performed after each
batch to verify the system is functioning correctly.

For each batch, the high level workflow is:

* remove the batch of hosts from the cluster
* reinstall the batch of hosts using CentOS 8 (out of scope for Kolla Ansible)
* bootstrap the batch of hosts
* deploy services to the batch of hosts
* verify the operation was successful

Controllers
###########

* :ref:`remove batch of CentOS 7 controllers from the cluster
  <removing-existing-controllers>`
* reinstall host OS using CentOS 8 (out of scope for Kolla Ansible)
* :ref:`add batch of CentOS 8 controllers to the cluster
  <adding-new-controllers>`
* verify the controllers are functioning correctly

Compute nodes
#############

* :ref:`remove batch of CentOS 7 compute nodes from the cluster
  <removing-existing-compute-nodes>`
* reinstall host OS using CentOS 8 (out of scope for Kolla Ansible)
* :ref:`add batch of CentOS 8 compute nodes to the cluster
  <adding-new-compute-nodes>`
* verify the compute nodes are functioning correctly
