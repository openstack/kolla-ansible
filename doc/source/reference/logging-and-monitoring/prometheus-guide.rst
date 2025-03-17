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

Note: This will deploy Prometheus version 2.x. Any potentially existing
Prometheus 1.x instances deployed by previous Kolla Ansible releases will
conflict with current version and should be manually stopped and/or removed.
If you would like to stay with version 1.x, set the ``enable_prometheus``
variable to ``no``.

In order to remove leftover volume containing Prometheus 1.x data, execute:

.. code-block:: console

   docker volume rm prometheus

on all hosts wherever Prometheus was previously deployed.

Basic Auth
~~~~~~~~~~

Prometheus is protected with basic HTTP authentication. Kolla-ansible will
create the following users: ``admin``, ``grafana`` (if grafana is
enabled) and ``skyline`` (if skyline is enabled). The grafana username can
be overridden using the variable
``prometheus_grafana_user``, the skyline username can
be overridden using the variable ``prometheus_skyline_user``.
The passwords are defined by the
``prometheus_password``, ``prometheus_grafana_password`` and
``prometheus_skyline_password`` variables in
``passwords.yml``. The list of basic auth users can be extended using the
``prometheus_basic_auth_users_extra`` variable:

.. code-block:: yaml

   prometheus_basic_auth_users_extra:
      - username: user
        password: hello
        enabled: true

or completely overridden with the ``prometheus_basic_auth_users`` variable.

Extending the default command line options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to extend the default command line options for Prometheus by
using a custom variable. As an example, to set query timeout to 1 minute
and data retention size to 30 gigabytes:

.. code-block:: yaml

   prometheus_cmdline_extras: "--query.timeout=1m --storage.tsdb.retention.size=30GB"

Configuration options
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Configuration options
   :widths: 25 25 75
   :header-rows: 1

   * - Option
     - Default
     - Description
   * - prometheus_scrape_interval
     - 60s
     - Default scrape interval for all jobs

Extending prometheus.cfg
~~~~~~~~~~~~~~~~~~~~~~~~

If you want to add extra targets to scrape, you can extend the default
``prometheus.yml`` config file by placing additional configs in
``{{ node_custom_config }}/prometheus/prometheus.yml.d``. These should have the
same format as ``prometheus.yml``. These additional configs are merged so
that any list items are extended. For example, if using the default value for
``node_custom_config``, you could add additional targets to scrape by defining
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
          - '{{ hostvars[host][('ansible_' + hostvars[host]['api_interface'] | replace('-','_'))]['ipv4']['address'] }}:{{ 3456 }}'
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
configuration. To enable you to do this, kolla-ansible will recursively
discover any files in ``{{ node_custom_config }}/prometheus/extras`` and
template them. The templated output is then copied to
``/etc/prometheus/extras`` within the container on startup. For example to
configure `ipmi_exporter <https://github.com/soundcloud/ipmi_exporter>`_, using
the default value for ``node_custom_config``, you could create the following
files:

* ``/etc/kolla/config/prometheus/prometheus.yml.d/ipmi-exporter.yml``:

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

*  ``/etc/kolla/config/prometheus/extras/file_sd/ipmi-exporter-targets.yml``:

   .. code-block:: yaml

      ---
      - targets:
        - 192.168.1.1
      labels:
          job: ipmi_exporter

Metric Instance labels
~~~~~~~~~~~~~~~~~~~~~~

Previously, Prometheus metrics used to label instances based on their IP
addresses. This behaviour can now be changed such that instances can be
labelled based on their inventory hostname instead. The IP address remains as
the target address, therefore, even if the hostname is unresolvable, it doesn't
pose an issue.

The default behavior still labels instances with their IP addresses. However,
this can be adjusted by changing the ``prometheus_instance_label`` variable.
This variable accepts the following values:

* ``None``: Instance labels will be IP addresses (default)
* ``{{ ansible_facts.hostname }}``: Instance labels will be hostnames
* ``{{ ansible_facts.nodename }}``: Instance labels will FQDNs

To implement this feature, modify the configuration file
``/etc/kolla/globals.yml`` and update the ``prometheus_instance_label``
variable accordingly. Remember, changing this variable will cause Prometheus to
scrape metrics with new names for a short period. This will result in duplicate
metrics until all metrics are replaced with their new labels.

.. code-block:: yaml

   prometheus_instance_label: "{{ ansible_facts.hostname }}"

This metric labeling feature may become the default setting in future releases.
Therefore, if you wish to retain the current default (IP address labels), make
sure to set the ``prometheus_instance_label`` variable to ``None``.

.. note::

   This feature may generate duplicate metrics temporarily while Prometheus
   updates the metric labels. Please be aware of this while analyzing metrics
   during the transition period.

Exporter configuration
~~~~~~~~~~~~~~~~~~~~~~

Node Exporter
-------------

Sometimes it can be useful to monitor hosts outside of the Kolla deployment.
One method of doing this is to configure a list of additional targets using the
``prometheus_node_exporter_targets_extra`` variable.  The format of which
should be a list of dictionaries with the following keys:

* target: URL of node exporter to scrape
* labels: (Optional) A list of labels to set on the metrics scaped from this
  exporter.

For example:

.. code-block:: yaml
  :caption: ``/etc/kolla/globals.yml``

  prometheus_node_exporter_targets_extra:
    - target: http://10.0.0.1:1234
      labels:
        instance: host1

Target address
~~~~~~~~~~~~~~

By default, Prometheus server uses the IP of the API interface of scrape
targets when collecting metrics. This may be overridden by setting
``prometheus_target_address`` as a host variable. The value of this host
variable must be a valid IPv4 or IPv6 address.

Prometheus server is one of the few instances where we need to know IP
addresses of all other hosts in the cloud. Being able to specify these via
``prometheus_target_address`` allows us to operate when facts are not available
for all hosts. This could be due to some hosts being unreachable or having
previously failed.
