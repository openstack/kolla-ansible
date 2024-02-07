=====================
Prometheus Monitoring
=====================

https://blueprints.launchpad.net/kolla-ansible/+spec/prometheus

One of the challenges faced by Kolla Ansible operators, particularly of large
deployments, is monitoring the behavior and performance of the nodes.  To help
address this concern, it is proposed that Kolla Ansible use Prometheus [1]_ as a
framework for introducing monitoring capabilities.

Prometheus is a widely adopted and supported tool for monitoring, capable of
monitoring both system and service level characteristics.  Many projects have
existing support for exporting data in Prometheus format either directly from
the product itself or via a separate exporter [2]_.  This includes several tools
used as part of the Kolla Ansible software stack, meaning that with minimal work
we could provide visibility into the performance characteristics of some of the
underlying software frameworks.  There are also exporters to do system
performance monitoring which could provide further visibility into the health of
the cluster.  Prometheus can also use the OpenStack APIs to automatically
discover running OpenStack servers such that servers can also easily expose data
to Prometheus.

Problem description
===================
There are three aspects to any useful system monitoring solution using
Prometheus:

* Exposing the data
* Configuring and running Prometheus to collect and store data
* Analyzing the data and reporting problems

Prometheus and existing exporters can help address the first two items above.
Analysis and reporting is the most complex part of the problem and will require
additional tools on top of Prometheus.  For example, Grafana can be configured
to use Prometheus as a data source and can help provide visibility into the data
collected by Prometheus.

Use Cases
---------
1. Query performance characteristics of nodes or other components in
   Kolla Ansible software stack (more details about what components can be
   monitored is given below)
2. Display dashboard illustrating overall system performance of Kolla Ansible
   nodes
3. Determine high-level status of Kolla Ansible containers and identify
   potential issues encountered during deployment

Proposed change
===============

Exposing the Data
-----------------
Prometheus generally works through a pull model where data is scraped at regular
intervals from data providers.  Therefore, the first step in any Prometheus
solution is to expose the data so that Prometheus can access it.

Some tools natively expose data in a useful format.  In these cases all that is
necessary is proper configuration of the tool to ensure the data is exported on
a known port and configuration of the Kolla Ansible container to expose the
relevant port such that Prometheus can access the data.

Most tools, however, use exporters or collectors that run as separate processes
from the tool itself.  These collect data using exposed APIs and format the data
in a manner that can be collected by Prometheus.  In these cases, each exporter
would be run on a separate container from the main process.  This will require
building of the requisite containers as well as modifications to the
Kolla Ansible deployment to run these containers during deployment. Furthermore,
each exporter requires configuration of the Prometheus server to configure it to
scrape the data.

Listed below are some of the exporters that already exist for Prometheus that
are related to components of a typical OpenStack Kolla Ansible deployment.  This
is based largely on the list of Prometheus Exporters and Integrations [2]_, and
links to more information about each exporter can be found there.  Although we
could choose to expose any of these exporters through Kolla Ansible, it is not
expected that we will implement all of these initially.  It is proposed that we
start with the exporters for which Kolla containers already exist.  cAdvisor is
also recommended for early implementation since it provides more detailed
metrics for Docker container performance.  We can investigate and add exporters
for additional services as time allows, but how far we proceed will depend
largely on the level of interest amongst Kolla Ansible developers who might help
do the work.

Existing Kolla Containers
^^^^^^^^^^^^^^^^^^^^^^^^^
The following exporters already have associated Kolla containers (used in
Kolla-Kubernetes) and therefore should be minimal work to make available for a
Kolla Ansible deployment:

* HAProxy
* MySQL
* Node Exporter - This exposes basic performance metrics (CPU, memory, IO, etc)
  on the host itself
* Prometheus - The Prometheus server contains support for monitoring its own
  performance without any need for an additional exporter

Other Possible Integrations
^^^^^^^^^^^^^^^^^^^^^^^^^^^
(in no particular order)

* cAdvisor
* OpenStack discovery - Prometheus contains support for discovering exposed
  services running on OpenStack instances.  It uses OpenStack client APIs to
  locate the instances and then can contact these instances that are accessible
  on the network and load Prometheus data from exporters running on those
  instances. It is not clear exactly how we would make use of this since we
  don't know what services might be running on the instances but it could be
  useful to set up access to a node exporter if it is running.  This not only
  provides insight into the instances' performance, but also would serve as a
  template for operators wishing to expose their own exporters from OpenStack
  instances.
* Docker - The existing Docker metric support is considered "experimental" and
  is subject to change so we may not want to use this until the API becomes more
  stable.
* Memcached
* ElasticSearch
* Fluentd
* Grafana
* Kafka
* InfluxDB

Kolla-Container Exporter
------------------------
One  piece of critical instrumentation is notably lacking from the existing
providers, and that is the ability to determine which Docker containers are
running on a node.  The existing Docker instrumentation can show how many
containers are running, but provides no visibility into which containers they
are.  The cAdvisor exporter also exposes information about containers (and
provides more detailed view into specific containers than the built-in Docker
metrics), but the high-level state of the container is still not available.
Determining which containers may have failed to start or are in the 'restarting'
state is one of the first troubleshooting steps of a broken Kolla Ansible
deployment, so this is a significant shortcoming.  Therefore, it is proposed
that a simple Prometheus collector be implemented that exposes this data to
Prometheus.

Initially this collector will be quite simple, but more functionality can be
added if and when we find more critical data missing from the existing set of
exporters or when additional health checking becomes available for Kolla Ansible
containers [3]_.  The key metric exposed by this collector is a gauge called
kolla_containers and has two labels, name and state which refer respectively to
the name of the container (e.g. cinder_volume) and the container state (e.g.
running).  Since the collector runs on each node, Prometheus will also
automatically add an implied label, instance, that indicates which node the
container is running on.  The value of the gauge is either 0 or 1 (1 indicating
the container with that name is in the indicated state).

A few examples of useful queries on this data include:

* Total number of Kolla Ansible containers across all nodes:
  ``sum(kolla_containers)``
* Number of containers in each state on each node: ``sum(kolla_containers) by
  (instance)``
* Number of containers in each state for a given service. For example, for
  cinder: ``sum(kolla_containers{name=~'cinder_.*'}) by (state)``
* A list of containers not in a normal (running) state:
  ``kolla_containers{state!="running"}``

This is just a sample list and other queries can be constructed to provide more
specific data.

The Kolla-Container collector uses the docker api to query this data and
connects via the unix socket.  It will use Python docker module to connect to
docker and the Prometheus_client module to expose this data in Prometheus
format.  It will filter the docker containers based on container label to only
expose statistics for Kolla Ansible containers.  Additionally, the collector
should expose certain standard metrics exposed by most collectors such as the
scrape duration which represents the performance characteristics of the
collector itself.

As with other collectors, this will run in its own docker container deployed via
the standard Ansible deployment.

Running Prometheus
------------------
Prometheus itself will run inside a container on each node in the existing
Kolla Ansible monitoring inventory group.  A Prometheus container already exists
in the Kolla repository (initially provided for Kolla-Kubernetes) and this
container can be used in Kolla Ansible deployment as well.

Additions will be required to the Kolla Ansible deployment process to run this
container.  Since this monitoring tool is useful in determining the state of
deployment and analyzing problems that may occur during deployment, the
container should be started as early as possible during deployment.  Although
Prometheus could be started even earlier, it is proposed that the Prometheus
deployment role be applied just after the MariaDB role since the Prometheus
MySQL exporter requires database user creation to function.

We should also expose Prometheus via HAProxy so that Prometheus data can be
queried using the virtual IP that is used to access other OpenStack APIs and
browser UIs.  This also will require modifications to the existing HAProxy
configuration template in the Kolla Ansible repository.

In the initial implementation, Prometheus will use local data storage for its
metrics.  This means that Prometheus data is not HA and there will be data
retention limits.  Each Prometheus server container will pull metrics
independently from the exporters and therefore the data may be different between
Prometheus servers.  In a future version (or if developer involvement and time
allow), it may be worth considering using external storage solutions to increase
capacity and allow for HA storage, such as can be provided using InfluxDB and
Influx-Relay as described at [4]_.

Data Analysis and Reporting
---------------------------
The Prometheus server can be directly queried to display and graph any of the
metrics collected by the server.  However, with the addition of Grafana, the
information may be organized into dashboards that collect multiple datapoints
into a single page and present them in a manner that is more useful to the
operator consuming this data.  In order to integrate with Grafana, Prometheus
would need to be defined as a datasource using the Grafana provisioning
framework.  Once that is done an operator can create or import dashboards that
make use of this data.

It would also be possible to define one or more default, preloaded dashboards
for Grafana to display the information deemed most useful for Kolla Ansible
deployment monitoring.  Grafana also has plugins that provide diagrams [5]_ that
could help visualize the state of the Kolla Ansible deployment.  The amount of
work that can be done in this area will depend upon the level of developer
interest and involvement in the project.

The addition of the data exported by the proposed Kolla-Container Exporter
provides a useful tool for checking the state of a Kolla Ansible deployment.  By
analyzing the data from this exporter, a tool can provide high-level deployment
status.  This functionality should be provided via a new status command within
the kolla-ansible command (or via a CLI if one is introduced [6]_).  Information
to be displayed will include:

* If Prometheus is not running or cannot be contacted, the status will indicate
  as such.  This could indicate that Prometheus is disabled, that deployment has
  not yet been initiated, or that deployment failed before the Prometheus
  container was started.  In this case, no further information can be provided.
* Nodes on which the Kolla-Container collector are not running should be
  highlighted since other information cannot be obtained on those nodes.  This
  will require correlating the instances on which the kolla_containers metric is
  exposed against the list of inventory hosts.  This could indicate a problem
  with the collector or with deployment of the collector, or it might just
  indicate that deployment has not yet proceeded to the point where the
  collector has been started.
* Kolla Ansible containers that are not in the running state should be listed.
  For example, containers in a restarting state may represent a misconfiguration
  of the cluster and should be identified.
* Other health statistics: on a normally running cluster, some basic statistics
  can be provided to help identify potential problems.  The set of statistics
  should include such details as the total number of running Kolla Ansible
  containers on each system (an unexpectedly low number on one or more systems
  might indicate a problem).  Other details can be added in the future as deemed
  necessary.
* Optional arguments could limit the output to a specific host, inventory group,
  or service.

Another common use of Prometheus is the use of a Prometheus Alertmanager which
is capable of sending alerts in cases where problems occur or predefined
thresholds are exceeded.  However, there are a number of complications regarding
the configuration and running of the Alertmanager, and the details are therefore
left for a future blueprint.

Configuration
-------------
As with all optional services in Kolla Ansible, Prometheus deployment should be
controlled by Kolla Ansible variables.  A high level enable_prometheus variable
should control whether Prometheus is used at all.  Additionally, additional
variables can be used to control individual exporters.  For example,
enable_prometheus_haproxy_exporter could be used to enable/disable the HAProxy
exporter to Prometheus.  By default Prometheus should be enabled and exporters
should be enabled if both Prometheus and the associated service are enabled.

Limitations
-----------
At it's core, Prometheus gathers numerical statistics about exposed services,
and provides a robust query language that allow an operator to query,
manipulate, and graph this data.  However, collecting and exposing this data is
really only half of any system monitoring solution.  Operators may not
understand the inner workings of the system enough for this data to be useful
without interpretation.  Prometheus can provide a lot of detailed data, but it
is not ideal for looking at a complex system and determining at a glance whether
it is running normally.  Initial integrations with Grafana and with a
kolla-ansible (or CLI) status command will provide useful data, but may prove
insufficient for many situations. However, even without more detailed analysis
tools, some benefit can still be drawn from merely collecting and storing the
data in Prometheus.  Knowledgeable operators can perform their own analysis as
long as the raw data is available.  Also, having the raw data available allows
us to incrementally improve on the complex problem of analysis and reporting
over subsequent releases.

Security Impact
---------------
A detailed analysis of the security model of Prometheus and its impact can be
found at [7]_.  In general, Prometheus considers collected metrics to be
insecure data accessible to anybody with access to the HTTP API.  For this
reason, Prometheus should only be exposed on the internal network interface and
VIP address and not exposed externally.  Operators who want to access Prometheus
data via the external network can access the data via the Grafana integration
which adds an additional security layer and requires a password to access any
data.

Performance Impact
------------------
Enabling Prometheus monitoring will have some impact on system performance.  It
adds a number of additional containers including one for each exporter and for
Prometheus itself.  Furthermore, the Prometheus server performs periodic
endpoint scraping where it queries each provider for the latest metrics.  The
impact of this data gathering will vary by exporter.  Although the impact of any
one exporter should be negligible, it's possible that in combination they might
have a measurable impact on the system.

Any potential risk to performance may be mitigated in several ways.  Each
exporter should be able to be enabled or disabled independently through
Kolla Ansible properties so if an exporter is found to have a significant
detrimental impact it may be disabled. In order to help determine any potential
impact, Prometheus provides metrics for monitoring its own performance, and most
exporters also include performance metrics for the exporters themselves.

Alternatives
------------
There are a number of possible alternatives to Prometheus for collecting,
maintaining, and exposing performance metrics.  Some of the primary options are
discussed at [8]_.  Another potential monitoring solution is Monasca which
provides a centralized service for both tenant and control plane monitoring.
Prometheus is more widely adopted and supported than many of the alternatives
and has rich support for many of the tools already used in the Kolla Ansible
software stack.  It's integration with Grafana provides an additional advantage
over some of the alternate solutions.

Implementation
==============

Assignee(s)
-----------
  Mark Giles (mark-giles)

Milestones
----------
Target Milestone for completion: Rocky 1

Work Items
----------
1. Prometheus server configuration for Kolla Ansible
2. Ansible deployment of existing Prometheus server container
3. Configuration of HAProxy to handle Prometheus server
4. Implement Kolla-Container Exporter
5. kolla-ansible (or CLI) status command to display Kolla-Container Exporter
   results
6. Integration with Grafana
7. Implement Grafana dashboard(s) to provide visualization of Kolla Ansible
   cluster behavior
8. Exporters (see below)

For each exporter, the following work items exist:

1. Create a Docker image for the exporter
2. Depending on the exporter, it may be necessary to modify settings for the
   monitored service's container to properly expose any necessary APIs
3. Implement Ansible deployment of the container
4. Modify Prometheus server configuration to scrape data from the exporter
5. (Optional) Implement or enhance Grafana dashboard(s) as appropriate.

The MySQL exporter in particular will require additional work:

6. Ansible definition to create Prometheus database user

Testing
=======
The existing gate checks will be used to ensure successful deployment.  Behavior
of the newly exposed functionality will require manual testing.

Documentation Impact
====================
A new documentation reference page should be created for "Prometheus in Kolla".
This page will document how to enable or disable Prometheus and/or individual
exporters as well as how to access the exposed data.

References
==========
.. [1] https://prometheus.io
.. [2] https://prometheus.io/docs/instrumenting/exporters/
.. [3] https://blueprints.launchpad.net/kolla/+spec/container-health-check
.. [4] https://docs.openstack.org/developer/performance-docs/methodologies/monitoring/influxha.html
.. [5] https://grafana.com/plugins/jdbranham-diagram-panel
.. [6] http://lists.openstack.org/pipermail/openstack-dev/2018-March/128561.html
.. [7] https://prometheus.io/docs/operating/security/
.. [8] https://prometheus.io/docs/introduction/comparison/
