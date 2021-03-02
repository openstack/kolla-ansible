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

This will, by default, deploy Prometheus version 2.x. Since Prometheus 1.x data
is not compatible with Prometheus 2.x and no automatic data migration is
provided, any previous Prometheus 1.x deployment will be replaced and all its
stored metrics will become inacessible (but still available in the old data
volume: ``prometheus``; the new data volume defaults to ``prometheus_v2``).
If you rely on Prometheus only as e.g. a source of alert notifications (in pair
with Alertmanager), it might not be worth migrating old metrics and they could
be discarded. Otherwise, it's either possible to use
`remote storage <https://prometheus.io/docs/prometheus/latest/storage/#remote-storage-integrations>`_
or scrape Kolla's Prometheus ``/federate`` endpoint with an external system.
However, if you want to stay on 1.x series, set the following variable:

.. code-block:: yaml

   prometheus_use_v1: yes

.. warning::
   Support for Prometheus 1.x is deprecated and will be removed in next
   Kolla Ansible release (Xena).

In order to remove leftover volume containing Prometheus 1.x data, execute:

.. code-block:: console

   docker volume rm prometheus

on all hosts wherever Prometheus was previously deployed.

Extending the default command line options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to extend the default command line options for Prometheus by
using a custom variable. As an example, to set query timeout to 1 minute
and data retention size to 30 gigabytes:

.. code-block:: yaml

   prometheus_cmdline_extras: "--query.timeout=1m --storage.tsdb.retention.size=30GB"

Extending prometheus.cfg
~~~~~~~~~~~~~~~~~~~~~~~~

If you want to add extra targets to scrape, you can extend the default
``prometheus.yml`` config file by placing additional configs in
``{{ node_custom_config }}/prometheus/prometheus.yml.d``. These should have the
same format as ``prometheus.yml``. These additional configs are merged so
that any list items are extended. For example, if using the default value for
``node_custom_config``, you could add additional targets to scape by defining
``/etc/kolla/config/prometheus/prometheus.yml.d/10-custom.yml`` containing the
following:

.. code-block:: jinja

  scrape_configs:
    - job_name: custom
      static_configs:
        - targets:
          - '10.0.0.111:1234'
    - job_name: custom-template
      static_configs:
        - targets:
  {% for host in groups['prometheus'] %}
          - '{{ hostvars[host]['ansible_' + hostvars[host]['api_interface']]['ipv4']['address'] }}:{{ 3456 }}'
  {% endfor %}

The jobs, ``custom``, and ``custom_template``  would be appended to the default
list of ``scrape_configs`` in the final ``prometheus.yml``. To customize on a per
host basis, files can also be placed in
``{{ node_custom_config }}/prometheus/<inventory_hostname>/prometheus.yml.d``
where, ``inventory_hostname`` is one of the hosts in your inventory. These
will be merged with any files in ``{{ node_custom_config }}/prometheus/prometheus.yml.d``,
so in order to override a list value instead of extending it, you will need to make
sure that no files in ``{{ node_custom_config }}/prometheus/prometheus.yml.d``
set a key with an equivalent hierarchical path.

Extra files
~~~~~~~~~~~

Sometimes it is necessary to reference additional files from within
``prometheus.yml``, for example, when defining file service discovery
configuration. To enable you to do this, kolla-ansible will resursively
discover any files in ``{{ node_custom_config }}/prometheus/extras`` and
template them. The templated output is then copied to
``/etc/prometheus/extras`` within the container on startup. For example to
configure `ipmi_exporter <https://github.com/soundcloud/ipmi_exporter>`_, using
the default value for ``node_custom_config``, you could create the following
files:

- ``/etc/kolla/config/prometheus/prometheus.yml.d/ipmi-exporter.yml``:

    .. code-block:: jinja

        ---
        scrape_configs:
        - job_name: ipmi
          params:
            module: ["default"]
            scrape_interval: 1m
            scrape_timeout: 30s
            metrics_path: /ipmi
            scheme: http
            file_sd_configs:
              - files:
                  - /etc/prometheus/extras/file_sd/ipmi-exporter-targets.yml
            refresh_interval: 5m
            relabel_configs:
              - source_labels: [__address__]
                separator: ;
                regex: (.*)
                target_label: __param_target
                replacement: ${1}
                action: replace
              - source_labels: [__param_target]
                separator: ;
                regex: (.*)
                target_label: instance
                replacement: ${1}
                action: replace
              - separator: ;
                regex: .*
                target_label: __address__
                replacement: "{{ ipmi_exporter_listen_address }}:9290"
                action: replace

  where ``ipmi_exporter_listen_address`` is a variable containing the IP address of
  the node where the exporter is running.

-  ``/etc/kolla/config/prometheus/extras/file_sd/ipmi-exporter-targets.yml``:
    .. code-block:: yaml

        ---
        - targets:
          - 192.168.1.1
        labels:
            job: ipmi_exporter
