.. _advanced-configuration:

======================
Advanced Configuration
======================

Endpoint Network Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When an OpenStack cloud is deployed, the REST API of each service is presented
as a series of endpoints. These endpoints are the internal URL, and the
external URL.

Kolla offers two options for assigning these endpoints to network addresses:

* Combined - Where both endpoints share the same IP address
* Separate - Where the external URL is assigned to an IP address that is
  different than the IP address used by the internal URL

The configuration parameters related to these options are:

* kolla_internal_vip_address
* network_interface
* kolla_external_vip_address
* kolla_external_vip_interface

For the combined option, set the two variables below, while allowing the
other two to accept their default values. In this configuration all REST
API requests, internal and external, will flow over the same network.

.. code-block:: yaml

   kolla_internal_vip_address: "10.10.10.254"
   network_interface: "eth0"

For the separate option, set these four variables. In this configuration
the internal and external REST API requests can flow over separate
networks.

.. code-block:: yaml

   kolla_internal_vip_address: "10.10.10.254"
   network_interface: "eth0"
   kolla_external_vip_address: "10.10.20.254"
   kolla_external_vip_interface: "eth1"

Fully Qualified Domain Name Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When addressing a server on the internet, it is more common to use
a name, like ``www.example.net``, instead of an address like
``10.10.10.254``. If you prefer to use names to address the endpoints
in your kolla deployment use the variables:

* kolla_internal_fqdn
* kolla_external_fqdn

.. code-block:: yaml

   kolla_internal_fqdn: inside.mykolla.example.net
   kolla_external_fqdn: mykolla.example.net

Provisions must be taken outside of kolla for these names to map to the
configured IP addresses. Using a DNS server or the ``/etc/hosts`` file
are two ways to create this mapping.

RabbitMQ Hostname Resolution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

RabbitMQ doesn't work with IP address, hence the IP address of
``api_interface`` should be resolvable by hostnames to make sure that
all RabbitMQ Cluster hosts can resolve each others hostname beforehand.

.. _tls-configuration:

TLS Configuration
~~~~~~~~~~~~~~~~~

Configuration of TLS is now covered :doc:`here <tls>`.

.. _service-config:

OpenStack Service Configuration in Kolla
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An operator can change the location where custom config files are read from by
editing ``/etc/kolla/globals.yml`` and adding the following line.

.. code-block:: yaml

   # The directory to merge custom config files the kolla's config files
   node_custom_config: "/etc/kolla/config"

Kolla allows the operator to override configuration of services. Kolla will
generally look for a file in ``/etc/kolla/config/<< config file >>``,
``/etc/kolla/config/<< service name >>/<< config file >>`` or
``/etc/kolla/config/<< service name >>/<< hostname >>/<< config file >>``,
but these locations sometimes vary and you should check the config task in
the appropriate Ansible role for a full list of supported locations. For
example, in the case of ``nova.conf`` the following locations are supported,
assuming that you have services using ``nova.conf`` running on hosts
called ``controller-0001``, ``controller-0002`` and ``controller-0003``:

* ``/etc/kolla/config/nova.conf``
* ``/etc/kolla/config/nova/controller-0001/nova.conf``
* ``/etc/kolla/config/nova/controller-0002/nova.conf``
* ``/etc/kolla/config/nova/controller-0003/nova.conf``
* ``/etc/kolla/config/nova/nova-scheduler.conf``

Using this mechanism, overrides can be configured per-project,
per-project-service or per-project-service-on-specified-host.

Overriding an option is as simple as setting the option under the relevant
section. For example, to set ``override scheduler_max_attempts`` in nova
scheduler, the operator could create
``/etc/kolla/config/nova/nova-scheduler.conf`` with content:

.. path /etc/kolla/config/nova/nova-scheduler.conf
.. code-block:: ini

   [DEFAULT]
   scheduler_max_attempts = 100

If the operator wants to configure compute node cpu and ram allocation ratio
on host myhost, the operator needs to create file
``/etc/kolla/config/nova/myhost/nova.conf`` with content:

.. path /etc/kolla/config/nova/myhost/nova.conf
.. code-block:: ini

   [DEFAULT]
   cpu_allocation_ratio = 16.0
   ram_allocation_ratio = 5.0

This method of merging configuration sections is supported for all services
using Oslo Config, which includes the vast majority of OpenStack services,
and in some cases for services using YAML configuration. Since the INI format
is an informal standard, not all INI files can be merged in this way. In
these cases Kolla supports overriding the entire config file.

Additional flexibility can be introduced by using Jinja conditionals in the
config files.  For example, you may create Nova cells which are homogeneous
with respect to the hypervisor model. In each cell, you may wish to configure
the hypervisors differently, for example the following override shows one way
of setting the ``bandwidth_poll_interval`` variable as a function of the cell:

.. path /etc/kolla/config/nova.conf
.. code-block:: ini

   [DEFAULT]
   {% if 'cell0001' in group_names %}
   bandwidth_poll_interval = 100
   {% elif 'cell0002' in group_names %}
   bandwidth_poll_interval = -1
   {% else %}
   bandwidth_poll_interval = 300
   {% endif %}

An alternative to Jinja conditionals would be to define a variable for the
``bandwidth_poll_interval`` and set it in according to your requirements
in the inventory group or host vars:

.. path /etc/kolla/config/nova.conf
.. code-block:: ini

   [DEFAULT]
   bandwidth_poll_interval = {{ bandwidth_poll_interval }}

Kolla allows the operator to override configuration globally for all services.
It will look for a file called ``/etc/kolla/config/global.conf``.

For example to modify database pool size connection for all services, the
operator needs to create ``/etc/kolla/config/global.conf`` with content:

.. path /etc/kolla/config/global.conf
.. code-block:: ini

   [database]
   max_pool_size = 100

OpenStack policy customisation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OpenStack services allow customisation of policy. Since the Queens release,
default policy configuration is defined within the source code for each
service, meaning that operators only need to override rules they wish to
change. Projects typically provide documentation on their default policy
configuration, for example, :keystone-doc:`Keystone <configuration/policy>`.

Policy can be customised via JSON or YAML files. As of the Wallaby release, the
JSON format is deprecated in favour of YAML. One major benefit of YAML is that
it allows for the use of comments.

For example, to customise the Neutron policy in YAML format, the operator
should add the customised rules in ``/etc/kolla/config/neutron/policy.yaml``.

The operator can make these changes after services have been deployed by using
the following command:

.. code-block:: console

   kolla-ansible deploy

In order to present a user with the correct interface, Horizon includes policy
for other services. Customisations made to those services may need to be
replicated in Horizon. For example, to customise the Neutron policy in YAML
format for Horizon, the operator should add the customised rules in
``/etc/kolla/config/horizon/neutron_policy.yaml``.

IP Address Constrained Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a development environment doesn't have a free IP address available for VIP
configuration, the host's IP address may be used here by disabling HAProxy by
adding:

.. code-block:: yaml

   enable_haproxy: "no"

Note this method is not recommended and generally not tested by the
Kolla community, but included since sometimes a free IP is not available
in a testing environment.

In this mode it is still necessary to configure ``kolla_internal_vip_address``,
and it should take the IP address of the ``api_interface`` interface.

External Elasticsearch/Kibana environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to use an external Elasticsearch/Kibana environment. To do this
first disable the deployment of the central logging.

.. code-block:: yaml

   enable_central_logging: "no"

Now you can use the parameter ``elasticsearch_address`` to configure the
address of the external Elasticsearch environment.

Non-default <service> port
~~~~~~~~~~~~~~~~~~~~~~~~~~

It is sometimes required to use a different than default port
for service(s) in Kolla. It is possible with setting
``<service>_port`` in ``globals.yml`` file. For example:

.. code-block:: yaml

   database_port: 3307

As ``<service>_port`` value is saved in different services' configuration so
it's advised to make above change before deploying.

Use an external Syslog server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, Fluentd is used as a syslog server to collect HAProxy
logs. When Fluentd is disabled or you want to use an external syslog server,
You can set syslog parameters in ``globals.yml`` file. For example:

.. code-block:: yaml

   syslog_server: "172.29.9.145"
   syslog_udp_port: "514"

You can also set syslog facility names for HAProxy logs.
By default, HAProxy uses ``local1``.

.. code-block:: yaml

   syslog_haproxy_facility: "local1"

If Glance TLS backend is enabled (``glance_enable_tls_backend``), the syslog
facility for the ``glance_tls_proxy`` service uses ``local2`` by default. This
can be set via ``syslog_glance_tls_proxy_facility``.

Mount additional Docker volumes in containers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is sometimes useful to be able to mount additional Docker volumes into
one or more containers. This may be to integrate 3rd party components into
OpenStack, or to provide access to site-specific data such as x.509
certificate bundles.

Additional volumes may be specified at three levels:

* globally
* per-service (e.g. nova)
* per-container (e.g. ``nova-api``)

To specify additional volumes globally for all containers, set
``default_extra_volumes`` in ``globals.yml``. For example:

.. code-block:: yaml

  default_extra_volumes:
    - "/etc/foo:/etc/foo"

To specify additional volumes for all containers in a service, set
``<service_name>_extra_volumes`` in ``globals.yml``. For example:

.. code-block:: yaml

  nova_extra_volumes:
    - "/etc/foo:/etc/foo"

To specify additional volumes for a single container, set
``<container_name>_extra_volumes`` in ``globals.yml``. For example:

.. code-block:: yaml

  nova_libvirt_extra_volumes:
    - "/etc/foo:/etc/foo"

Migrate container engine
~~~~~~~~~~~~~~~~~~~~~~~~

Kolla-Ansible supports two container engines - Docker and Podman.
It is possible to migrate deployed OpenStack between these two engines.
Migration is supported in both directions, meaning it is possible to
migrate from Docker to Podman as well as from Podman to Docker.

Before starting the migration, you have to change the value of
``kolla_container_engine`` in your ``/etc/kolla/globals.yml`` file to the new
container engine:

.. code-block:: yaml

   # previous value was docker
   kolla_container_engine: podman

Apart from this change, ``globals.yml`` should stay unchanged.
The same goes for any other config file, such as the inventory file.

.. warning::

   Currently, rolling migration is not supported. You have to stop
   all virtual machines running in your OpenStack. Otherwise,
   migration will become unstable and can fail.

After editing ``globals.yml`` and stopping virtual machines
migration can be started with the following command:

.. code-block:: console

   kolla-ansible migrate-container-engine

.. warning::
   During the migration, all the container volumes will be migrated
   under the new container engine. Old container engine system packages will be
   removed from the system and all their resources and data will be deleted.
