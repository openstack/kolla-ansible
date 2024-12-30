=========================
Adding and removing hosts
=========================

This page discusses how to add and remove nodes from an existing cluster. The
procedure differs depending on the type of nodes being added or removed, which
services are running, and how they are configured. Here we will consider two
types of nodes - controllers and compute nodes. Other types of nodes will need
consideration.

Any procedure being used should be tested before being applied in a production
environment.

Adding new hosts
================

.. _adding-new-controllers:

Adding new controllers
----------------------

The :doc:`bootstrap-servers command
</reference/deployment-and-bootstrapping/bootstrap-servers>` can be used to
prepare the new hosts that are being added to the system.  It adds an entry to
``/etc/hosts`` for the new hosts, and some services, such as RabbitMQ, require
entries to exist for all controllers on every controller. If using a
``--limit`` argument, ensure that all controllers are included, e.g. via
``--limit control``. Be aware of the :ref:`potential issues <rebootstrapping>`
with running ``bootstrap-servers`` on an existing system.

.. code-block:: console

   kolla-ansible bootstrap-servers -i <inventory> [ --limit <limit> ]

Pull down container images to the new hosts. The ``--limit`` argument may be
used and only needs to include the new hosts.

.. code-block:: console

   kolla-ansible pull -i <inventory> [ --limit <limit> ]

Deploy containers to the new hosts. If using a ``--limit`` argument, ensure
that all controllers are included, e.g. via ``--limit control``.

.. code-block:: console

   kolla-ansible deploy -i <inventory> [ --limit <limit> ]

The new controllers are now deployed. It is recommended to perform testing
of the control plane at this point to verify that the new controllers are
functioning correctly.

Some resources may not be automatically balanced onto the new controllers. It
may be helpful to manually rebalance these resources onto the new controllers.
Examples include networks hosted by Neutron DHCP agent, and routers hosted by
Neutron L3 agent. The `removing-existing-controllers`_ section provides an
example of how to do this.

.. _adding-new-compute-nodes:

Adding new compute nodes
------------------------

The :doc:`bootstrap-servers command
</reference/deployment-and-bootstrapping/bootstrap-servers>`, can be used to
prepare the new hosts that are being added to the system.  Be aware of the
:ref:`potential issues <rebootstrapping>` with running ``bootstrap-servers`` on
an existing system.

.. code-block:: console

   kolla-ansible bootstrap-servers -i <inventory> [ --limit <limit> ]

Pull down container images to the new hosts. The ``--limit`` argument may be
used and only needs to include the new hosts.

.. code-block:: console

   kolla-ansible pull -i <inventory> [ --limit <limit> ]

Deploy containers on the new hosts. The ``--limit`` argument may be used and
only needs to include the new hosts.

.. code-block:: console

   kolla-ansible deploy -i <inventory> [ --limit <limit> ]

The new compute nodes are now deployed. It is recommended to perform
testing of the compute nodes at this point to verify that they are functioning
correctly.

Server instances are not automatically balanced onto the new compute nodes. It
may be helpful to live migrate some server instances onto the new hosts.

.. code-block:: console

   openstack server migrate <server> --live-migration --host <target host> --os-compute-api-version 2.30

Alternatively, a service such as :watcher-doc:`Watcher </>` may be used to do
this automatically.

Removing existing hosts
=======================

.. _removing-existing-controllers:

Removing existing controllers
-----------------------------

When removing controllers or other hosts running clustered services, consider
whether enough hosts remain in the cluster to form a quorum. For example, in a
system with 3 controllers, only one should be removed at a time. Consider also
the effect this will have on redundancy.

Before removing existing controllers from a cluster, it is recommended to move
resources they are hosting. Here we will cover networks hosted by Neutron DHCP
agent and routers hosted by Neutron L3 agent. Other actions may be necessary,
depending on your environment and configuration.

For each host being removed, find Neutron routers on that host and move them.
Disable the L3 agent. For example:

.. code-block:: console

   l3_id=$(openstack network agent list --host <host> --agent-type l3 -f value -c ID)
   target_l3_id=$(openstack network agent list --host <target host> --agent-type l3 -f value -c ID)
   openstack router list --agent $l3_id -f value -c ID | while read router; do
     openstack network agent remove router $l3_id $router --l3
     openstack network agent add router $target_l3_id $router --l3
   done
   openstack network agent set $l3_id --disable

Repeat for DHCP agents:

.. code-block:: console

   dhcp_id=$(openstack network agent list --host <host> --agent-type dhcp -f value -c ID)
   target_dhcp_id=$(openstack network agent list --host <target host> --agent-type dhcp -f value -c ID)
   openstack network list --agent $dhcp_id -f value -c ID | while read network; do
     openstack network agent remove network $dhcp_id $network --dhcp
     openstack network agent add network $target_dhcp_id $network --dhcp
   done

Stop all services running on the hosts being removed:

.. code-block:: console

   kolla-ansible stop -i <inventory> --yes-i-really-really-mean-it [ --limit <limit> ]

Remove the hosts from the Ansible inventory.

Reconfigure the remaining controllers to update the membership of clusters such
as MariaDB and RabbitMQ. Use a suitable limit, such as ``--limit control``.

.. code-block:: console

   kolla-ansible deploy -i <inventory> [ --limit <limit> ]

Perform testing to verify that the remaining cluster hosts are operating
correctly.

For each host, clean up its services:

.. code-block:: console

   openstack network agent list --host <host> -f value -c ID | while read id; do
     openstack network agent delete $id
   done

   openstack compute service list --os-compute-api-version 2.53 --host <host> -f value -c ID | while read id; do
     openstack compute service delete --os-compute-api-version 2.53 $id
   done

If the node is also running the ``etcd`` service, set
``etcd_remove_deleted_members: "yes"`` in ``globals.yml`` to automatically
remove nodes from the ``etcd`` cluster that have been removed from the inventory.

Alternatively the ``etcd`` members can be removed manually with ``etcdctl``.
For more details, please consult the ``runtime reconfiguration`` documentation
section for the version of etcd in operation.

.. _removing-existing-compute-nodes:

Removing existing compute nodes
-------------------------------

When removing compute nodes from a system, consider whether there is capacity
to host the running workload on the remaining compute nodes. Include overhead
for failures that may occur.

Before removing compute nodes from a system, it is recommended to migrate or
destroy any instances that they are hosting.

For each host, disable the compute service to ensure that no new instances are
scheduled to it.

.. code-block:: console

   openstack compute service set <host> nova-compute --disable

If possible, live migrate instances to another host.

.. code-block:: console

   openstack server list --all-projects --host <host> -f value -c ID | while read server; do
     openstack server migrate --live-migration $server
   done

Verify that the migrations were successful.

Stop all services running on the hosts being removed:

.. code-block:: console

   kolla-ansible stop -i <inventory> --yes-i-really-really-mean-it [ --limit <limit> ]

Remove the hosts from the Ansible inventory.

Perform testing to verify that the remaining cluster hosts are operating
correctly.

For each host, clean up its services:

.. code-block:: console

   openstack network agent list --host <host> -f value -c ID | while read id; do
     openstack network agent delete $id
   done

   openstack compute service list --os-compute-api-version 2.53 --host <host> -f value -c ID | while read id; do
     openstack compute service delete --os-compute-api-version 2.53 $id
   done
