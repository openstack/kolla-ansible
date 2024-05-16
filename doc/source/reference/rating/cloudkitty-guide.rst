.. _cloudkitty-guide:

=================================
CloudKitty - Rating service guide
=================================

Overview
~~~~~~~~
CloudKitty is the Openstack service used to rate your platform usage.
As a rating service, CloudKitty does not provide billing services such as
generating a bill to send to your customers every month.

However, it provides you the building bricks you can use to build your own
billing service upon internally.

Because cloudkitty is a flexible rating service, it's highly customizable while
still offering a generic approach to the rating of your platform.

It lets you choose which metrics you want to rate, from which datasource
and where to finally store the processed rate of those resources.

This document will explain how to use the different features available and that
Kolla Ansible supports.

See the :cloudkitty-doc:`CloudKitty documentation </>` for further information.

CloudKitty Collector backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CloudKitty natively supports multiple collector backends.

By default Kolla Ansible uses the Gnocchi backend. Using data
collected by Prometheus is also supported.

The configuration parameter related to this option is
``cloudkitty_collector_backend``.

To use the Prometheus collector backend:

.. code-block:: yaml

   cloudkitty_collector_backend: prometheus

CloudKitty Fetcher Backend
~~~~~~~~~~~~~~~~~~~~~~~~~~

CloudKitty natively supports multiple fetcher backends.

By default Kolla Ansible uses the ``keystone`` backend. This can be changed
using the ``cloudkitty_fetcher_backend`` option.

Kolla Ansible also supports the ``prometheus`` backend type, which is
configured to discover scopes from the ``id`` label of the
``openstack_identity_project_info`` metric of OpenStack exporter.

You will need to provide extra configuration for unsupported fetchers in
``/etc/kolla/config/cloudkitty.conf``.

Cloudkitty Storage Backend
~~~~~~~~~~~~~~~~~~~~~~~~~~

As for collectors, CloudKitty supports multiple backend to store ratings.
By default, Kolla Ansible uses the InfluxDB based backend.

Another famous alternative is OpenSearch and can be activated in Kolla
Ansible using the ``cloudkitty_storage_backend`` configuration option in
your ``globals.yml`` configuration file:

.. code-block:: yaml

   cloudkitty_storage_backend: opensearch

Using an external Elasticsearch backend is still possible with the following
configuration:

.. code-block:: yaml

   cloudkitty_storage_backend: elasticsearch
   cloudkitty_elasticsearch_url: http://HOST:PORT

You can only use one backend type at a time, selecting ``opensearch``
will automatically enable OpenSearch deployment and creation of the
required CloudKitty index.
