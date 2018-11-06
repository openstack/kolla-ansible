.. _monasca-guide:

================
Monasca in Kolla
================

Overview
~~~~~~~~

Monasca provides monitoring and logging as-a-service for OpenStack. It
consists of a large number of micro-services coupled together by Apache
Kafka. If it is enabled in Kolla, it is automatically configured to collect
logs and metrics from across the control plane. These logs and metrics
are accessible from the Monasca APIs to anyone with credentials for
the OpenStack project to which they are posted.

Monasca is not just for the control plane. Monitoring data can just as
easily be gathered from tenant deployments, by for example baking the
Monasca Agent into the tenant image, or installing it post-deployment
using an orchestration tool.

Finally, one of the key tenets of Monasca is that it is scalable. In Kolla
Ansible, the deployment has been designed from the beginning to work in a
highly available configuration across multiple nodes. Traffic is typically
balanced across multiple instances of a service by HAProxy, or in other
cases using the native load balancing mechanism provided by the service.
For example, topic partitions in Kafka. Of course, if you start out with
a single server that's fine too, and if you find that you need to improve
capacity later on down the line, adding additional nodes should be a
fairly straightforward exercise.

Pre-deployment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable Monasca in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_monasca: "yes"

Currently Monasca is only supported using the ``source`` install type Kolla
images. If you are using the ``binary`` install type you should set the
following override in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   monasca_install_type: "source"

Until the Monasca Kafka client is upgraded it is currently required
to run Kafka in compatibility mode. This can be achieved by adding some
custom Kafka configuration:

.. code-block:: console

   echo "log.message.format.version=0.9.0.0" >> /etc/kolla/config/kafka.server.properties

Finally it should be noted that support for Kibana and Grafana integration has
not yet been enabled. This will be added in the future.

Building images
~~~~~~~~~~~~~~~

To build any custom images required by Monasca see the instructions in the
Kolla repo: `kolla/doc/source/admin/template-override/monasca.rst`. The
remaining images may be pulled from Docker Hub, but if you need to build
them manually you can use the following commands:

.. code-block:: console

   $ kolla-build -t source monasca
   $ kolla-build kafka zookeeper storm elasticsearch logstash kibana grafana

If you want to deploy Monasca standalone you will also need the following
images:

.. code-block:: console

   $ kolla-build cron fluentd mariadb kolla-toolbox keystone memcached keepalived haproxy

Note that deploying Monasca standalone isn't fully supported yet, and it's
likely that you'll want to integrate with an external Keystone deployment
for tight integration with your OpenStack deployment,

Deployment
~~~~~~~~~~

Run the deploy as usual:

.. code-block:: console

   $ kolla-ansible deploy

System requirements and performance impact
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Monasca will deploy the following Docker containers:

* Apache Kafka
* Apache Storm
* Apache Zookeeper
* Elasticsearch
* Grafana
* InfluxDB
* Kibana
* Monasca Agent Collector
* Monasca Agent Forwarder
* Monasca Agent Statsd
* Monasca API
* Monasca Log API
* Monasca Log Transformer (Logstash)
* Monasca Log Metrics (Logstash)
* Monasca Log Perister (Logstash)
* Monasca Notification
* Monasca Persister
* Monasca Thresh (Apache Storm topology)

In addition to these, Monasca will also utilise Kolla deployed MariaDB,
Keystone, Memcached and HAProxy/Keepalived. The Monasca Agent containers
will, by default, be deployed on all nodes managed by Kolla Ansible. This
includes all nodes in the control plane as well as compute, storage and
monitoring nodes.

Whilst these services will run on an all-in-one deployment, in a production
environment it is recommended to use at least one dedicated monitoring node
to avoid the risk of starving core OpenStack services of resources. As a
general rule of thumb, for a standalone monitoring server running Monasca
in a production environment, you will need at least 32GB RAM and a recent
multi-core CPU. You will also need enough space to store metrics and logs,
and to buffer these in Kafka. Whilst Kafka is happy with spinning disks,
you will likely want to use SSDs to back InfluxDB and Elasticsearch.

Security Impact
~~~~~~~~~~~~~~~

The Monasca API and the Monasca Log API will be exposed on public endpoints
via HAProxy/Keepalived.

If you are using the multi-tenant capabilities of Monasca there is a risk
that tenants could gain access to other tenants logs and metrics. This could
include logs and metrics for the control plane which could reveal sensitive
information about the size and nature of the deployment.

A full evaluation of attack vectors is outside the scope of this document.

Assignee
~~~~~~~~

Monasca support in Kolla was contributed by StackHPC Ltd. and the Kolla
community. If you have any issues with the deployment please ask in the
Kolla IRC channel.
