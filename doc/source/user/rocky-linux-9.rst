.. _Migrating to Rocky Linux 9:

==========================
Migrating to Rocky Linux 9
==========================

From Zed onwards, CentOS Stream 8 is not supported in Kolla and Kolla-Ansible.
As a result, it is recommended that deployments using CentOS Stream 8 hosts and
containers are migrated to Rocky Linux 9 to upgrade past Yoga.

It is possible to perform a rolling migration to ensure service is not
disrupted. This section covers the steps required to perform such a migration.

Overview
========

For hosts running CentOS 8 Stream, the migration process has a simple
structure:

#. Remove a CentOS Stream 8 host from service
#. Reprovision it with a Rocky Linux 9 image (outside the scope of
   Kolla-Ansible and this guide)
#. Configure and deploy the host with Rocky Linux 9 containers

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
perform a rolling migration between two different OS distributions, hosts must
to be deployed with different containers. This should not cause any disruption
to service, however it will require configuration changes where it is assumed
that the host OS is the same across all hosts.

There are multiple ways to achieve this, such as using group variables to
choose container tags. The simplest way is to template  ``kolla_base_distro``
based on ``ansible_facts.distribution`` which will be gathered on a per-host
basis. This can be set in globals.yml

.. code-block:: yaml

    kolla_base_distro: "{{ ansible_facts.distribution }}"


Controller migration
====================

A general guide for removing a controller node from service can be found on the
`adding-and-removing-hosts <https://docs.openstack.org/kolla-ansible/yoga/user/adding-and-removing-hosts.html#removing-existing-controllers>`__
page. There are some additional steps to take if the deployment is using OVN.
If you are not sure whether this applies, check whether the controllers have an
``ovn_nb_db`` container. If they do, the deployment is using OVN. The steps
listed below should be executed just before stopping all the services on the
host.

Once the controller has been completely removed from service, it should be
reprovisioned with a Rocky Linux 9 host image, which can be found
`here <https://dl.rockylinux.org/pub/rocky/9/images/>`__. The exact process for
doing so is outside the scope of this guide and Kolla-Ansible in general.

Once provisioned, the controller can be returned to service. A guide for doing
so is available
`here <https://docs.openstack.org/kolla-ansible/yoga/user/adding-and-removing-hosts.html#adding-new-controllers>`__.

Common pitfalls
---------------

* It is always recommended that you back up your database before undertaking
  major maintenance work. Instructions for how to do so can be found
  `here <https://docs.openstack.org/kolla-ansible/latest/admin/mariadb-backup-and-restore.html>`__.
* Some instability has been observed in MariaDB mid-way through migration. It
  does not appear to consistently be an issue, but the safest way to mitigate
  the risk is to run the MariaDB recovery tool after migrating each controller:

  .. code-block:: bash

    kolla-ansible -i INVENTORY mariadb_recovery

  The symptoms of the problem are random failures on some but not all API
  requests. This means any interaction with the cloud e.g. creating a server,
  will occasionally fail. If these errors start to occur, they can usually be
  resolved by successively restarting the MariaDB containers on each
  controller.
* This migration relies on recent changes to kolla-ansible, which are
  detailed
  `here <https://review.opendev.org/c/openstack/kolla-ansible/+/868929>`__.
  Without these changes, OVN can become unstable when redeploying controllers.
  Ensure your deployment is using the latest stable release before continuing.

OVN Graceful Shutdown Procedure
-------------------------------

#.  Exec into the OVN Northbound container, ``ovn_nb_db``. It is best to do so on
    every controller, or at least the controller to remove and one other
    controller.

    .. code-block:: bash

        sudo docker exec -it ovn_nb_db bash

#.  Check the cluster state in each container.

    .. code-block:: bash

        ovs-appctl -t /run/ovn/ovnnb_db.ctl cluster/status OVN_Northbound

    All controllers should be listed in the cluster at this point.

#.  Leave the cluster, only on the controller to be migrated.

    .. code-block:: bash

        ovs-appctl -t /run/ovn/ovnnb_db.ctl cluster/leave OVN_Northbound

#.  Again check the cluster state.

    .. code-block:: bash

        ovs-appctl -t /run/ovn/ovnnb_db.ctl cluster/status OVN_Northbound

    All controllers except the one being migrated should be in the cluster.

#.  Now repeat the process in the OVN Southbound container. Exec into
    ``ovn_sb_db``. It is best to do so on every controller, or at least the
    controller to remove and one other controller.

    .. code-block:: bash

        sudo docker exec -it ovn_sb_db bash

#.  Check the cluster state in each container.

    .. code-block:: bash

        ovs-appctl -t /run/ovn/ovnsb_db.ctl cluster/status OVN_Southbound

    All controllers should be listed in this cluster at this point.

#.  Leave the cluster, only on the controller to be migrated.

    .. code-block:: bash

        ovs-appctl -t /run/ovn/ovnsb_db.ctl cluster/leave OVN_Southbound

#.  Again check the cluster state.

    .. code-block:: bash

        ovs-appctl -t /run/ovn/ovnsb_db.ctl cluster/status OVN_Southbound

    All controllers except the one being migrated should be in the cluster.

#.  It is now safe to stop all services on the host. The process does not need
    to be repeated in reverse when adding a new controller to the deployment.
    The hosts should be able to join the cluster without issue.


Compute node migration
======================

As long as sufficient compute capacity is available, compute nodes are arguably
the easiest nodes to migrate. The general process for compute node removal is
to disable the compute service on the host, which stops any new instances being
provisioned on the machine, then migrate any active instances away, and finally
disable all services on the node. A guide with additional detail is available
`here <https://docs.openstack.org/kolla-ansible/yoga/user/adding-and-removing-hosts.html#removing-existing-compute-nodes>`__.

Once the compute node has been completely removed from service, it should be
reprovisioned with a Rocky Linux 9 host image, which can be found
`here <https://dl.rockylinux.org/pub/rocky/9/images/>`__. The exact process for
doing so is outside the scope of this guide and Kolla-Ansible in general.

Once provisioned, the compute node can be returned to service. A guide for
doing so is available
`here <https://docs.openstack.org/kolla-ansible/yoga/user/adding-and-removing-hosts.html#adding-new-compute-nodes>`__.

As with the controller migration, it is important that any Rocky Linux 9
containers are built using the latest release of Kolla. This is a particular
concern for deployments using Ceph-backed storage. There was previously a bug
in Kolla that prevented the live migration of instances to hosts using Rocky
Linux 9 with Ceph-backed storage. It was patched in May 2023. This bug would
make it impossible to progress without serious disruption to service since
instances could not be migrated from old CentOS Stream 8 hosts onto new Rocky
Linux 9 hosts.

