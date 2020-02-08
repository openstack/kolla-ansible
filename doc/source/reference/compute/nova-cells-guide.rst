==========
Nova Cells
==========

Overview
========

Nova cells V2 is a feature that allows Nova deployments to be scaled out to
a larger size than would otherwise be possible. This is achieved through
sharding of the compute nodes into pools known as *cells*, with each cell
having a separate message queue and database.

Further information on cells can be found in the Nova documentation
:nova-doc:`here <user/cells.html>` and :nova-doc:`here
<user/cellsv2-layout.html>`. This document assumes the reader is familiar with
the concepts of cells.

Cells: deployment perspective
=============================

From a deployment perspective, nova cell support involves separating the Nova
services into two sets - global services and per-cell services.

Global services:

* ``nova-api``
* ``nova-scheduler``
* ``nova-super-conductor`` (in multi-cell mode)

Per-cell control services:

* ``nova-compute-ironic`` (for Ironic cells)
* ``nova-conductor``
* ``nova-novncproxy``
* ``nova-serialproxy``
* ``nova-spicehtml5proxy``

Per-cell compute services:

* ``nova-compute``
* ``nova-libvirt``
* ``nova-ssh``

Another consideration is the database and message queue clusters that the cells
depend on. This will be discussed later.

Service placement
-----------------

There are a number of ways to place services in a multi-cell environment.

Single cell topology
~~~~~~~~~~~~~~~~~~~~

The single cell topology is used by default, and is limited to a single cell::

            +----------------+
            |                ++
            |                |-+
            |   controllers  |-|
            |                |-|
            |                |-|
            +------------------|
             +-----------------|
              +----------------+

    +--------------+     +--------------+
    |              |     |              |
    |   cell 1     |     |   cell 1     |
    |   compute 1  |     |   compute 2  |
    |              |     |              |
    +--------------+     +--------------+

All control services run on the controllers, and there is no superconductor.

Dedicated cell controller topology
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this topology, each cell has a dedicated group of controllers to run cell
control services. The following diagram shows the topology for a cloud with two
cells::

                                    +----------------+
                                    |                ++
                                    |                |-+
                                    |   controllers  |-|
                                    |                |-|
                                    |                |-|
                                    +------------------|
                                     +-----------------|
                                      +----------------+

                       +----------------+        +----------------+
                       |                ++       |                ++
                       |   cell 1       |-+      |   cell 2       |-+
                       |   controllers  |-|      |   controllers  |-|
                       |                |-|      |                |-|
                       +------------------|      +------------------|
                        +-----------------|       +-----------------|
                         +----------------+        +----------------+

    +--------------+     +--------------+        +--------------+     +--------------+
    |              |     |              |        |              |     |              |
    |   cell 1     |     |   cell 1     |        |   cell 2     |     |   cell 2     |
    |   compute 1  |     |   compute 2  |        |   compute 1  |     |   compute 2  |
    |              |     |              |        |              |     |              |
    +--------------+     +--------------+        +--------------+     +--------------+

Shared cell controller topology
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

   This topology is not yet supported by Kolla Ansible.

An alternative configuration is to place the cell control services for multiple
cells on a single shared group of cell controllers. This might allow for more
efficient use of hardware where the control services for a single cell do not
fully consume the resources of a set of cell controllers::

                                    +----------------+
                                    |                ++
                                    |                |-+
                                    |   controllers  |-|
                                    |                |-|
                                    |                |-|
                                    +------------------|
                                     +-----------------|
                                      +----------------+

                                    +----------------+
                                    |                ++
                                    |   shared cell  |-+
                                    |   controllers  |-|
                                    |                |-|
                                    +------------------|
                                     +-----------------|
                                      +----------------+

    +--------------+     +--------------+        +--------------+     +--------------+
    |              |     |              |        |              |     |              |
    |   cell 1     |     |   cell 1     |        |   cell 2     |     |   cell 2     |
    |   compute 1  |     |   compute 2  |        |   compute 1  |     |   compute 2  |
    |              |     |              |        |              |     |              |
    +--------------+     +--------------+        +--------------+     +--------------+

Databases & message queues
--------------------------

The global services require access to a database for the API and cell0
databases, in addition to a message queue. Each cell requires its own database
and message queue instance. These could be separate database and message queue
clusters, or shared database and message queue clusters partitioned via
database names and virtual hosts. Currently Kolla Ansible supports deployment
of shared database cluster and message queue clusters.

Configuration
=============

.. seealso::

   Configuring Kolla Ansible for deployment of multiple cells typically
   requires use of :ref:`inventory host and group variables
   <multinode-host-and-group-variables>`.

Enabling multi-cell support
---------------------------

Support for deployment of multiple cells is disabled by default - nova is
deployed in single conductor mode.

Deployment of multiple cells may be enabled by setting ``enable_cells`` to
``yes`` in ``globals.yml``. This deploys nova in superconductor mode, with
separate conductors for each cell.

Naming cells
------------

By default, all cell services are deployed in a single unnamed cell. This
behaviour is backwards compatible with previous releases of Kolla Ansible.

To deploy hosts in a different cell, set the ``nova_cell_name`` variable
for the hosts in the cell. This can be done either using host variables or
group variables.

Groups
------

In a single cell deployment, the following Ansible groups are used to determine
the placement of services:

* ``compute``: ``nova-compute``, ``nova-libvirt``, ``nova-ssh``
* ``nova-compute-ironic``: ``nova-compute-ironic``
* ``nova-conductor``: ``nova-conductor``
* ``nova-novncproxy``: ``nova-novncproxy``
* ``nova-serialproxy``: ``nova-serialproxy``
* ``nova-spicehtml5proxy``: ``nova-spicehtml5proxy``

In a multi-cell deployment, this is still necessary - compute hosts must be in
the ``compute`` group. However, to provide further control over where cell
services are placed, the following variables are used:

* ``nova_cell_compute_group``
* ``nova_cell_compute_ironic_group``
* ``nova_cell_conductor_group``
* ``nova_cell_novncproxy_group``
* ``nova_cell_serialproxy_group``
* ``nova_cell_spicehtml5proxy_group``

For backwards compatibility, these are set by default to the original group
names.  For a multi-cell deployment, they should be set to the name of a group
containing only the compute hosts in that cell.

Example
~~~~~~~

In the following example we have two cells, ``cell1`` and ``cell2``. Each cell
has two compute nodes and a cell controller.

Inventory:

.. code-block:: INI

   [compute:children]
   compute-cell1
   compute-cell2

   [nova-conductor:children]
   cell-control-cell1
   cell-control-cell2

   [nova-novncproxy:children]
   cell-control-cell1
   cell-control-cell2

   [nova-spicehtml5proxy:children]
   cell-control-cell1
   cell-control-cell2

   [nova-serialproxy:children]
   cell-control-cell1
   cell-control-cell2

   [cell1:children]
   compute-cell1
   cell-control-cell1

   [cell2:children]
   compute-cell2
   cell-control-cell2

   [compute-cell1]
   compute01
   compute02

   [compute-cell2]
   compute03
   compute04

   [cell-control-cell1]
   cell-control01

   [cell-control-cell2]
   cell-control02

Cell1 group variables (``group_vars/cell1``):

.. code-block:: yaml

   nova_cell_name: cell1
   nova_cell_compute_group: compute-cell1
   nova_cell_conductor_group: cell-control-cell1
   nova_cell_novncproxy_group: cell-control-cell1
   nova_cell_serialproxy_group: cell-control-cell1
   nova_cell_spicehtml5proxy_group: cell-control-cell1

Cell2 group variables (``group_vars/cell2``):

.. code-block:: yaml

   nova_cell_name: cell2
   nova_cell_compute_group: compute-cell2
   nova_cell_conductor_group: cell-control-cell2
   nova_cell_novncproxy_group: cell-control-cell2
   nova_cell_serialproxy_group: cell-control-cell2
   nova_cell_spicehtml5proxy_group: cell-control-cell2

Note that these example cell group variables specify groups for all console
proxy services for completeness. You will need to ensure that there are no
port collisions. For example, if in both cell1 and cell2, you use the default
``novncproxy`` console proxy, you could add ``nova_novncproxy_port: 6082``
to the cell2 group variables to prevent a collision with cell1.

Databases
---------

The database connection for each cell is configured via the following
variables:

* ``nova_cell_database_name``
* ``nova_cell_database_user``
* ``nova_cell_database_password``
* ``nova_cell_database_address``
* ``nova_cell_database_port``

By default the MariaDB cluster deployed by Kolla Ansible is used.  For an
unnamed cell, the ``nova`` database is used for backwards compatibility.  For a
named cell, the database is named ``nova_<cell name>``.

Message queues
--------------

The RPC message queue for each cell is configured via the following variables:

* ``nova_cell_rpc_user``
* ``nova_cell_rpc_password``
* ``nova_cell_rpc_port``
* ``nova_cell_rpc_group_name``
* ``nova_cell_rpc_transport``
* ``nova_cell_rpc_vhost``

And for notifications:

* ``nova_cell_notify_user``
* ``nova_cell_notify_password``
* ``nova_cell_notify_port``
* ``nova_cell_notify_group_name``
* ``nova_cell_notify_transport``
* ``nova_cell_notify_vhost``

By default the message queue cluster deployed by Kolla Ansible is used. For an
unnamed cell, the ``/`` virtual host used by all OpenStack services is used for
backwards compatibility.  For a named cell, a virtual host named ``nova_<cell
name>`` is used.

Conductor & API database
------------------------

By default the cell conductors are configured with access to the API database.
This is currently necessary for `some operations
<https://docs.openstack.org/nova/latest/user/cellsv2-layout.html#operations-requiring-upcalls>`__
in Nova which require an *upcall*.

If those operations are not required, it is possible to prevent cell conductors
from accessing the API database by setting
``nova_cell_conductor_has_api_database`` to ``no``.

Console proxies
---------------

General information on configuring console access in Nova is available
:ref:`here <nova-consoles>`. For deployments with multiple cells, the console
proxies for each cell must be accessible by a unique endpoint. We achieve this
by adding an HAProxy frontend for each cell that forwards to the console
proxies for that cell. Each frontend must use a different port. The port may be
configured via the following variables:

* ``nova_novncproxy_port``
* ``nova_spicehtml5proxy_port``
* ``nova_serialproxy_port``

Ironic
------

Currently all Ironic-based instances are deployed in a single cell. The name of
that cell is configured via ``nova_cell_ironic_cell_name``, and defaults to the
unnamed cell. ``nova_cell_compute_ironic_group`` can be used to set the group
that the ``nova-compute-ironic`` services are deployed to.

Deployment
==========

Deployment in a multi-cell environment does not need to be done differently
than in a single-cell environment - use the ``kolla-ansible deploy`` command.

Scaling out
-----------

A common operational task in large scale environments is to add new compute
resources to an existing deployment. In a multi-cell environment it is likely
that these will all be added to one or more new or existing cells. Ideally we
would not risk affecting other cells, or even the control hosts, when deploying
these new resources.

The Nova cells support in Kolla Ansible has been built such that it is possible
to add new cells or extend existing ones without affecting the rest of the
cloud. This is achieved via the ``--limit`` argument to ``kolla-ansible``. For
example, if we are adding a new cell ``cell03`` to an existing cloud, and all
hosts for that cell (control and compute) are in a ``cell03`` group, we could
use this as our limit:

.. code-block:: console

   kolla-ansible deploy --limit cell03

When adding a new cell, we also need to ensure that HAProxy is configured for
the console proxies in that cell:

.. code-block:: console

   kolla-ansible deploy --tags haproxy

Another benefit of this approach is that it should be faster to complete, as
the number of hosts Ansible manages is reduced.

.. _nova-cells-upgrade:

Upgrades
========

Similar to deploys, upgrades in a multi-cell environment can be performed in
the same way as single-cell environments, via ``kolla-ansible upgrade``.

Staged upgrades
---------------

.. note::

   Staged upgrades are not applicable when ``nova_safety_upgrade`` is ``yes``.

In large environments the risk involved with upgrading an entire site can be
significant, and the ability to upgrade one cell at a time is crucial. This
is very much an advanced procedure, and operators attempting this should be
familiar with the :nova-doc:`Nova upgrade documentation <user/upgrade>`.

Here we use Ansible tags and limits to control the upgrade process. We will
only consider the Nova upgrade here. It is assumed that all dependent services
have been upgraded (see ``ansible/site.yml`` for correct ordering).

The first step, which may be performed in advance of the upgrade, is to perform
the database schema migrations.

.. code-block:: console

   kolla-ansible upgrade --tags nova-bootstrap

Next, we upgrade the global services.

.. code-block:: console

   kolla-ansible upgrade --tags nova-api-upgrade

Now the cell services can be upgraded. This can be performed in batches of
one or more cells at a time, using ``--limit``. For example, to upgrade
services in ``cell03``:

.. code-block:: console

   kolla-ansible upgrade --tags nova-cell-upgrade --limit cell03

At this stage, we might wish to perform testing of the new services, to check
that they are functioning correctly before proceeding to other cells.

Once all cells have been upgraded, we can reload the services to remove RPC
version pinning, and perform online data migrations.

.. code-block:: console

   kolla-ansible upgrade --tags nova-reload,nova-online-data-migrations

The nova upgrade is now complete, and upgrading of other services may continue.
