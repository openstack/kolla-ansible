.. _influxdb-guide:

===============================
InfluxDB - Time Series Database
===============================

Overview
~~~~~~~~

InfluxDB is a time series database developed by InfluxData. It is
possible to deploy a single instance without charge. To use the
clustering features you will require a commercial license.

InfluxDB
~~~~~~~~

The `recommendation <https://docs.influxdata.com/influxdb/v1.7/guides/hardware_sizing/#what-kind-of-storage-do-i-need>`_
is to use flash storage for InfluxDB. If docker is configured to use
spinning disks by default, or you have some higher performance drives
available, it may be desirable to control where the docker volume is
located. This can be achieved by setting a path for
``influxdb_datadir_volume`` in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

    influxdb_datadir_volume: /mnt/ssd/influxdb/

The default is to use a named volume, ``influxdb``.
