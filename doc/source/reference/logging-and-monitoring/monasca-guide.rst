.. _monasca-guide:

============================
Monasca - Monitoring service
============================

Overview
~~~~~~~~

Following a decline in activity within the OpenStack Monasca project,
Kolla Ansible has decided to remove support for deploying it. Advice
for removing it is included in the cleanup section below.

Cleanup
~~~~~~~

The cleanup command can be invoked from the Kolla Ansible CLI, for example:

.. code-block:: console

   kolla-ansible monasca_cleanup

This will remove Monasca service containers (including Kafka, Storm and
ZooKeeper), and service configuration.

Following cleanup, you may also choose to remove unused container volumes.
It is recommended to run this manually on each Monasca service host. Note
that `docker prune` will indiscriminately remove all unused volumes,
which may not always be what you want. If you wish to keep a subset of
unused volumes, you can remove them individually.

To remove all unused volumes on a host:

.. code-block:: console

   docker prune

To remove a single unused volume, run for example:

.. code-block:: console

   docker volume rm monasca_log_transformer_data

Assignee
~~~~~~~~

Monasca support in Kolla was contributed by StackHPC Ltd. and the Kolla
community. If you have any issues with the deployment please ask in the
Kolla IRC channel.
