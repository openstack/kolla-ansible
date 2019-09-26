.. _prometheus-guide:

=====================================================
Prometheus - Monitoring System & Time Series Database
=====================================================

Overview
~~~~~~~~

Kolla can deploy a full working Prometheus setup in either a **all-in-one** or
**multinode** setup.

Preparation and deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~

To enable Prometheus, modify the configuration file ``/etc/kolla/globals.yml``
and change the following:

.. code-block:: yaml

   enable_prometheus: "yes"

Extending the default command line options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to extend the default command line options for Prometheus by
using a custom variable. As an example, to set remote timeouts to 30 seconds
and data retention period to 2 days:

.. code-block:: yaml

   prometheus_cmdline_extras: "-storage.remote.timeout 30s -storage.local.retention 48h"
