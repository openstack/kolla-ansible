.. _advanced-configuration:

======================
Advanced Configuration
======================

Endpoint Network Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When an OpenStack cloud is deployed, the REST API of each service is presented
as a series of endpoints. These endpoints are the admin URL, the internal
URL, and the external URL.

Kolla offers two options for assigning these endpoints to network addresses:
- Combined - Where all three endpoints share the same IP address
- Separate - Where the external URL is assigned to an IP address that is
different than the IP address shared by the internal and admin URLs

The configuration parameters related to these options are:
- kolla_internal_vip_address
- network_interface
- kolla_external_vip_address
- kolla_external_vip_interface

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

- kolla_internal_fqdn
- kolla_external_fqdn

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

TLS Configuration
~~~~~~~~~~~~~~~~~

An additional endpoint configuration option is to enable or disable
TLS protection for the internal and/or external VIP. TLS allows a client to
authenticate the OpenStack service endpoint and allows for encryption of the
requests and responses.

The configuration variables that control TLS networking are:

- kolla_enable_tls_external
- kolla_external_fqdn_cert
- kolla_enable_tls_internal
- kolla_internal_fqdn_cert

.. note::

   If TLS is enabled only on the internal or the external network
   the kolla_internal_vip_address and kolla_external_vip_address must
   be different.

   If there is only a single network configured in your network topology
   (opposed to configuring seperate internal and external networks), TLS
   can be enabled using only the internal network configuration variables.

The default for TLS is disabled, to enable TLS networking:

.. code-block:: yaml

   kolla_enable_tls_external: "yes"
   kolla_external_fqdn_cert: "{{ kolla_certificates_dir }}/mycert.pem"

   and/or

   kolla_enable_tls_internal: "yes"
   kolla_internal_fqdn_cert: "{{ kolla_certificates_dir }}/mycert-internal.pem"


.. note::

   TLS authentication is based on certificates that have been
   signed by trusted Certificate Authorities. Examples of commercial
   CAs are Comodo, Symantec, GoDaddy, and GlobalSign. Letsencrypt.org
   is a CA that will provide trusted certificates at no charge. Many
   company's IT departments will provide certificates within that
   company's domain. If using a trusted CA is not possible for your
   situation, you can use `OpenSSL <https://www.openssl.org>`__
   to create your own company's domain or see the section below about
   kolla generated self-signed certificates.

Two certificate files are required to use TLS securely with authentication.
These two files will be provided by your Certificate Authority. These
two files are the server certificate with private key and the CA certificate
with any intermediate certificates. The server certificate needs to be
installed with the kolla deployment and is configured with the
``kolla_external_fqdn_cert`` or ``kolla_internal_fqdn_cert`` parameter.
If the server certificate provided is not already trusted by the client,
then the CA certificate file will need to be distributed to the client.

When using TLS to connect to a public endpoint, an OpenStack client will
have settings similar to this:

.. code-block:: shell

   export OS_PROJECT_DOMAIN_ID=default
   export OS_USER_DOMAIN_ID=default
   export OS_PROJECT_NAME=demo
   export OS_USERNAME=demo
   export OS_PASSWORD=demo-password
   export OS_AUTH_URL=https://mykolla.example.net:5000
   # os_cacert is optional for trusted certificates
   export OS_CACERT=/etc/pki/ca/mykolla-cacert.crt
   export OS_IDENTITY_API_VERSION=3

Self-Signed Certificates
~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

   Self-signed certificates should never be used in production.

It is not always practical to get a certificate signed by a well-known
trust CA, for example a development or internal test kolla deployment. In
these cases it can be useful to have a self-signed certificate to use.

For convenience, the ``kolla-ansible`` command will generate the necessary
certificate files based on the information in the ``globals.yml``
configuration file:

.. code-block:: console

   kolla-ansible certificates

The certificate file haproxy.pem will be generated and stored in the
``/etc/kolla/certificates/`` directory, and the CA cert will be in the
``/etc/kolla/certificates/ca/`` directory.

Adding CA Certificates to the Service Containers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To copy CA certificate files to the service containers

.. code-block:: yaml

   kolla_copy_ca_into_containers: "yes"

When ``kolla_copy_ca_into_containers`` is configured to "yes", the
CA certificate files in /etc/kolla/certificates/ca will be copied into
service containers to enable trust for those CA certificates. This is required
for any certificates that are either self-signed or signed by a private CA,
and are not already present in the service image trust store.

All certificate file names will have the "kolla-customca-" prefix prepended to
it when it is copied into the containers. For example, if a certificate file is
named "internal.crt", it will be named "kolla-customca-internal.crt" in the
containers.

For Debian and Ubuntu containers, the certificate files will be copied to
the ``/usr/local/share/ca-certificates/`` directory.

For Centos and Red Hat Linux containers, the certificate files will be copied
to the ``/etc/pki/ca-trust/source/anchors/`` directory.

In addition, the ``openstack_cacert`` should be configured with the path to
the cacert in the container. For example, if the self-signed certificate task
was used and the deployment is on ubuntu, the path would be:
"/etc/pki/ca-trust/source/anchors/kolla-customca-haproxy-internal.crt"

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

In case the operators want to customize ``policy.json`` file, they should
create a full policy file for specific project in the same directory like above
and Kolla will overwrite default policy file with it. Be aware, with some
projects are keeping full policy file in source code, operators just need to
copy it but with some others are defining default rules in codebase, they have
to generate it.

For example to overwrite ``policy.json`` file of Neutron project, the operator
needs to grab ``policy.json`` from Neutron project source code, update rules
and then put it to ``/etc/kolla/config/neutron/policy.json``.

.. note::

   Currently kolla-ansible only support JSON and YAML format for policy file.

The operator can make these changes after services were already deployed by
using following command:

.. code-block:: console

   kolla-ansible reconfigure

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

By default, Fluentd is used as a syslog server to collect Swift and HAProxy
logs. When Fluentd is disabled or you want to use an external syslog server,
You can set syslog parameters in ``globals.yml`` file. For example:

.. code-block:: yaml

   syslog_server: "172.29.9.145"
   syslog_udp_port: "514"

You can also set syslog facility names for Swift and HAProxy logs.
By default, Swift and HAProxy use ``local0`` and ``local1``, respectively.

.. code-block:: yaml

   syslog_swift_facility: "local0"
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
