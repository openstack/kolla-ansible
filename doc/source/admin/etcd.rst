.. etcd:

=============
Managing etcd
=============

Kolla Ansible can manage the lifecycle of an etcd cluster and supports the
following operations:

* Bootstrapping a clean multi-node etcd cluster.
* Adding a new member to the etcd cluster.
* Optionally, automatically removing a deleted node from the etcd cluster.

It is highly recommended to read the operator documentation for the version
of etcd deployed in the cluster.

.. note::

   Once an etcd cluster is bootstrapped, the etcd service takes most of its
   configuration from the etcd database itself.

   This pattern is very different from many other Kolla Ansible services, and
   is a source of confusion for operators unfamiliar with etcd.

Cluster vs. Node Bootstrapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible distinguishes between two forms of bootstrapping in an etcd
cluster:

* Bootstrapping multiple nodes at the same time to bring up a new cluster.
* Bootstrapping a single node to add it to an existing cluster.

These corresponds to the ``new`` and ``existing`` parameters for
``ETCD_INITIAL_CLUSTER_STATE`` in the upstream documentation. Once an etcd node
has completed bootstrap, the bootstrap configuration is ignored, even if it is
changed.

Kolla Ansible will decide to perform a new cluster bootstrap if it detects that
there is no existing data on the etcd nodes. Otherwise it assumes that there is
a healthy etcd cluster and it will add a new node to it.

Forcing Bootstrapping
~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible looks for the ``kolla_etcd`` volume on the node. If this volume
is available, it assumes that the bootstrap process has run on the node and
the volume contains the required config.

However, if the process was interrupted (externally, or by an error), this
volume might be misconfigured. In order to prevent data loss, manual
intervention is required.

Before retriggering bootstrap make sure that there is no valuable data on the
volume. This could be because the node was not in service, or that the data
is persisted elsewhere.

To retrigger a bootstrap (for either the cluster, or for a single node),
remove the volume from all affected nodes by running:

.. code-block:: console

   docker volume rm kolla_etcd

Rerunning Kolla Ansible will then trigger the appropriate workflow and either
a blank cluster will be bootstrapped, or an empty member will be added to
the existing cluster.

Manual Commands
~~~~~~~~~~~~~~~

In order to manage etcd manually, the ``etcdctl`` command can be used inside
the ``etcd`` container. This command has been set up with the appropriate
environment variables for integrating with automation.

``etcdctl`` is configured with json output by default, you can override that
if you are running it yourself:

.. code-block:: console

   # list cluster members in a human-readable table
   docker exec -it etcd etcdctl -w table member list

Removing Dead Nodes
~~~~~~~~~~~~~~~~~~~

If ``globals.yml`` has the value ``etcd_remove_deleted_members: "yes"`` then
etcd nodes that are not in the inventory will be removed from the etcd cluster.

Any errors in the inventory can therefore cause unintended removal.

To manually remove a dead node from the etcd cluster, use the following
commands:

.. code-block:: console

   # list cluster members and identify dead member
   docker exec -it etcd etcdctl -w table member list
   # remove dead member
   docker exec -it etcd etcdctl member remove MEMBER_ID_IN_HEX
