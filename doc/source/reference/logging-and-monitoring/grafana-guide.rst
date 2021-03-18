.. _grafana-guide:

=======
Grafana
=======

Overview
~~~~~~~~

`Grafana <https://grafana.com>`_ is open and composable observability and
data visualization platform. Visualize metrics, logs, and traces from
multiple sources like Prometheus, Loki, Elasticsearch, InfluxDB,
Postgres and many more..

Preparation and deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~

To enable Grafana, modify the configuration file ``/etc/kolla/globals.yml``
and change the following:

.. code-block:: yaml

   enable_grafana: "yes"

If you would like to set up Prometheus as a data source, additionally set:

.. code-block:: yaml

   enable_prometheus: "yes"

Please follow :doc:`Prometheus Guide <prometheus-guide>` for more information.

Custom dashboards provisioning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible sets custom dashboards provisioning using `Dashboard provider <https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards>`_.

Dashboard's JSON files should be placed into
``{{ node_custom_config }}/grafana/dashboards/`` folder.
Dashboards will be imported to Grafana dashboards General Folder.

Grafana provisioner config can be altered by placing ``provisioning.yaml`` to
``{{ node_custom_config }}/grafana/`` folder.

For other settings, follow configuration reference:
`Dashboard provider configuration <https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards>`_.
