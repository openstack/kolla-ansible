.. _kafka-guide:

============
Apache Kafka
============

Overview
~~~~~~~~

`Kafka <https://kafka.apache.org/intro>`_ is a distributed stream processing
system. It forms the central component of Monasca and in an OpenStack context
can also be used as an experimental messaging backend in `Oslo messaging
<https://docs.openstack.org/oslo.messaging/latest/admin/kafka.html>`_.

Kafka
~~~~~

A spinning disk array is normally sufficient for Kafka. The data directory
defaults to a docker volume, ``kafka``. Since it can use a lot of disk space,
you may wish to store the data on a dedicated device. This can be achieved by
setting ``kafka_datadir_volume`` in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

    kafka_datadir_volume: /mnt/spinning_array/kafka/
