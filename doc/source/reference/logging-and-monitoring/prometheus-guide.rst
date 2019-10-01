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
