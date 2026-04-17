.. _Migrating to Rocky Linux 10:

===========================
Migrating to Rocky Linux 10
===========================

Kolla Ansible 2025.1 (Epoxy) supports both Rocky Linux 9 and Rocky Linux 10.
As a result, it is recommended that deployments using Rocky Linux 9 hosts and
containers are migrated to Rocky Linux 10 before upgrading to 2025.2
(Flamingo) or 2026.1 (Gazpacho).

It is possible to perform a rolling migration to ensure service is not
disrupted. This section covers the steps required to perform such a migration.

Overview
========

For hosts running Rocky Linux 9, the migration process has a simple structure:

#. Remove a Rocky Linux 9 host from service
#. Reprovision it with a Rocky Linux 10 image (outside the scope of
   Kolla-Ansible and this guide)
#. Configure and deploy the host with Rocky Linux 10 containers

While it is technically possible to migrate hosts in any order, it is strongly
recommended that migrations for one type of node are completed before moving on
to the next i.e. all compute node migrations are performed before all storage
node migrations.

The order of node groups is less important, however it is arguably safest to
perform controller node migrations first, given that they are the most complex
and it is easiest to revert their state in the event of a failure.

Container Images
================

In a standard deployment, the container images are consistent across hosts. To
perform a rolling migration between two different host OS major versions, hosts
must be deployed with different containers. This should not cause any
disruption to service, however it will require configuration changes where it
is assumed that the host OS is the same across all hosts.

There are multiple ways to achieve this, such as using group variables to
choose container tags. The simplest way is to template
``kolla_base_distro_version`` based on
``ansible_facts.distribution_major_version`` which will be gathered on a
per-host basis. This can be set in ``globals.yml``:

.. code-block:: yaml

    kolla_base_distro: "rocky"
    kolla_base_distro_version: "{{ ansible_facts.distribution_major_version }}"

Controller migration
====================

A general guide for removing a controller node from service can be found in the
:ref:`removing-existing-controllers` section. There are some additional steps
to take if the deployment is using OVN. If you are not sure whether this
applies, check whether the controllers have an
``ovn_nb_db`` container. If they do, the deployment is using OVN. The steps
listed below should be executed just before stopping all the services on the
host.

Once the controller has been completely removed from service, it should be
reprovisioned with a Rocky Linux 10 host image, which can be found
`here <https://dl.rockylinux.org/pub/rocky/10/images/>`__. The exact process
for doing so is outside the scope of this guide and Kolla-Ansible in general.

Once provisioned, the controller can be returned to service. A guide for doing
so is available in the :ref:`adding-new-controllers` section.

Common pitfalls
---------------

* It is always recommended that you back up your database before undertaking
  major maintenance work. Instructions for how to do so can be found in
  :doc:`/admin/mariadb-backup-and-restore`.
* If your deployment uses Redis, complete the :ref:`migrate-redis-to-valkey`
  procedure before migrating controllers to Rocky Linux 10.

OVN Graceful Shutdown Procedure
-------------------------------

#. Exec into the OVN Northbound container, ``ovn_nb_db``. It is best to do so
   on every controller, or at least the controller to remove and one other
   controller.

   .. code-block:: bash

      sudo docker exec -it ovn_nb_db bash

#. Check the cluster state in each container.

   .. code-block:: bash

      ovs-appctl -t /var/run/ovn/ovnnb_db.ctl cluster/status OVN_Northbound

   All controllers should be listed in the cluster at this point.

#. Leave the cluster, only on the controller to be migrated.

   .. code-block:: bash

      ovs-appctl -t /var/run/ovn/ovnnb_db.ctl cluster/leave OVN_Northbound

#. Again check the cluster state.

   .. code-block:: bash

      ovs-appctl -t /var/run/ovn/ovnnb_db.ctl cluster/status OVN_Northbound

   All controllers except the one being migrated should be in the cluster.

#. Now repeat the process in the OVN Southbound container. Exec into
   ``ovn_sb_db``. It is best to do so on every controller, or at least the
   controller to remove and one other controller.

   .. code-block:: bash

      sudo docker exec -it ovn_sb_db bash

#. Check the cluster state in each container.

   .. code-block:: bash

      ovs-appctl -t /var/run/ovn/ovnsb_db.ctl cluster/status OVN_Southbound

   All controllers should be listed in this cluster at this point.

#. Leave the cluster, only on the controller to be migrated.

   .. code-block:: bash

      ovs-appctl -t /var/run/ovn/ovnsb_db.ctl cluster/leave OVN_Southbound

#. Again check the cluster state.

   .. code-block:: bash

      ovs-appctl -t /var/run/ovn/ovnsb_db.ctl cluster/status OVN_Southbound

   All controllers except the one being migrated should be in the cluster.

#. It is now safe to stop all services on the host. The process does not need
   to be repeated in reverse when adding a new controller to the deployment.
   The hosts should be able to join the cluster without issue.


Compute node migration
======================

As long as sufficient compute capacity is available, compute nodes are arguably
the easiest nodes to migrate. The general process for compute node removal is
to disable the compute service on the host, which stops any new instances being
provisioned on the machine, then migrate any active instances away, and finally
disable all services on the node. A guide with additional detail is available
in the :ref:`removing-existing-compute-nodes` section.

Once the compute node has been completely removed from service, it should be
reprovisioned with a Rocky Linux 10 host image, which can be found
`here <https://dl.rockylinux.org/pub/rocky/10/images/>`__. The exact process
for doing so is outside the scope of this guide and Kolla-Ansible in general.

Once provisioned, the compute node can be returned to service. A guide for
doing so is available in the :ref:`adding-new-compute-nodes` section.

As with the controller migration, it is important that any Rocky Linux 10
containers are built using a Kolla release that includes Rocky Linux 10
support.
