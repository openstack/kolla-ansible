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

Pre-deployment configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable Monasca in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_monasca: "yes"

Currently Monasca is only supported using the ``source`` install type Kolla
images. If you are using the ``binary`` install type you should set the
following override in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   monasca_install_type: "source"

Stand-alone configuration (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Monasca can be deployed via Kolla-Ansible in a standalone configuration. The
deployment will include all supporting services such as HAProxy, Keepalived,
MariaDB and Memcached. It can also include Keystone, but you will likely
want to integrate with the Keystone instance provided by your existing
OpenStack deployment. Some reasons to perform a standalone deployment are:

* Your OpenStack deployment is *not* managed by Kolla-Ansible, but you want
  to take advantage of Monasca support in Kolla-Ansible.
* Your OpenStack deployment *is* managed by Kolla-Ansible, but you do not
  want the Monasca deployment to share services with your OpenStack
  deployment. For example, in a combined deployment Monasca will share HAProxy
  and MariaDB with the core OpenStack services.
* Your OpenStack deployment *is* managed by Kolla-Ansible, but you want
  Monasca to be decoupled from the core OpenStack services. For example, you
  may have a dedicated monitoring and logging team, and wish to prevent that
  team accidentally breaking, or redeploying core OpenStack services.
* You want to deploy Monasca for testing. In this case you will likely want
  to deploy Keystone as well.

To configure a standalone installation you will need to add the following to
`/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_nova: "no"
   enable_neutron: "no"
   enable_heat: "no"
   enable_openvswitch: "no"
   enable_horizon: "no"
   enable_glance: "no"
   enable_rabbitmq: "no"

With the above configuration alone Keystone *will* be deployed. If you want
Monasca to be registered with an external instance of Keystone you can
add the following, additional configuration to `/etc/kolla/globals.yml`:

.. code-block:: yaml

   enable_keystone: "no"
   keystone_admin_url: "http://172.28.128.254:35357"
   keystone_internal_url: "http://172.28.128.254:5000"
   monasca_openstack_auth:
     auth_url: "{{ keystone_admin_url }}"
     username: "admin"
     password: "{{ external_keystone_admin_password }}"
     project_name: "admin"
     domain_name: "default"
     user_domain_name: "default"

In this example it is assumed that the external Keystone admin and internal
URLs are `http://172.28.128.254:35357` and `http://172.28.128.254:5000`
respectively, and that the external Keystone admin password is defined by
the variable `external_keystone_admin_password` which you will most likely
want to save in `/etc/kolla/passwords.yml`. Note that the Keystone URLs can
be obtained from the external OpenStack CLI, for example:

.. code-block:: console

   openstack endpoint list --service identity
   +----------------------------------+-----------+--------------+--------------+---------+-----------+-----------------------------+
   | ID                               | Region    | Service Name | Service Type | Enabled | Interface | URL                         |
   +----------------------------------+-----------+--------------+--------------+---------+-----------+-----------------------------+
   | 162365440e6c43d092ad6069f0581a57 | RegionOne | keystone     | identity     | True    | admin     | http://172.28.128.254:35357 |
   | 6d768ee2ce1c4302a49e9b7ac2af472c | RegionOne | keystone     | identity     | True    | public    | http://172.28.128.254:5000  |
   | e02067a58b1946c7ae53abf0cfd0bf11 | RegionOne | keystone     | identity     | True    | internal  | http://172.28.128.254:5000  |
   +----------------------------------+-----------+--------------+--------------+---------+-----------+-----------------------------+

If you are also using Kolla-Ansible to manage the external OpenStack
installation, the external Keystone admin password will most likely
be defined in the *external* `/etc/kolla/passwords.yml` file. For other
deployment methods you will need to consult the relevant documentation.

Building images
~~~~~~~~~~~~~~~

To build any custom images required by Monasca see the instructions in the
Kolla repo: `kolla/doc/source/admin/template-override/monasca.rst`. The
remaining images may be pulled from Docker Hub, but if you need to build
them manually you can use the following commands:

.. code-block:: console

   $ kolla-build -t source monasca
   $ kolla-build kafka zookeeper storm elasticsearch logstash kibana grafana

If you are deploying Monasca standalone you will also need the following
images:

.. code-block:: console

   $ kolla-build cron fluentd mariadb kolla-toolbox keystone memcached keepalived haproxy

Deployment
~~~~~~~~~~

Run the deploy as usual, following whichever procedure you normally use
to decrypt secrets if you have encrypted them with Ansible Vault:

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

Security impact
~~~~~~~~~~~~~~~

The Monasca API and the Monasca Log API will be exposed on public endpoints
via HAProxy/Keepalived.

If you are using the multi-tenant capabilities of Monasca there is a risk
that tenants could gain access to other tenants logs and metrics. This could
include logs and metrics for the control plane which could reveal sensitive
information about the size and nature of the deployment.

Another risk is that users may gain access to system logs via Kibana, which
is not accessed via the Monasca APIs. Whilst Kolla configures a password out
of the box to restrict access to Kibana, the password will not apply if a
user has access to the network on which the individual Kibana service(s) bind
behind HAProxy. Note that Elasticsearch, which is not protected by a
password, will also be directly accessible on this network, and therefore
great care should be taken to ensure that untrusted users do not have access
to it.

A full evaluation of attack vectors is outside the scope of this document.

Assignee
~~~~~~~~

Monasca support in Kolla was contributed by StackHPC Ltd. and the Kolla
community. If you have any issues with the deployment please ask in the
Kolla IRC channel.
