.. _rabbitmq:

========
RabbitMQ
========

RabbitMQ is a message broker written in Erlang.
It is currently the default provider of message queues in Kolla Ansible
deployments.

TLS encryption
~~~~~~~~~~~~~~

There are a number of channels to consider when securing RabbitMQ
communication. Kolla Ansible currently supports TLS encryption of the
following:

* client-server traffic, typically between OpenStack services using the
  :oslo.messaging-doc:`oslo.messaging </>` library and RabbitMQ
* RabbitMQ Management API and UI (frontend connection to HAProxy only)

Encryption of the following channels is not currently supported:

* RabbitMQ cluster traffic between RabbitMQ server nodes
* RabbitMQ CLI communication with RabbitMQ server nodes

Client-server
-------------

Encryption of client-server traffic is enabled by setting
``rabbitmq_enable_tls`` to ``true``. Additionally, certificates and keys must
be available in the following paths (in priority order):

Certificates:

* ``"{{ kolla_certificates_dir }}/{{ inventory_hostname }}/rabbitmq-cert.pem"``
* ``"{{ kolla_certificates_dir }}/{{ inventory_hostname }}-cert.pem"``
* ``"{{ kolla_certificates_dir }}/rabbitmq-cert.pem"``

Keys:

* ``"{{ kolla_certificates_dir }}/{{ inventory_hostname }}/rabbitmq-key.pem"``
* ``"{{ kolla_certificates_dir }}/{{ inventory_hostname }}-key.pem"``
* ``"{{ kolla_certificates_dir }}/rabbitmq-key.pem"``

The default for ``kolla_certificates_dir`` is ``/etc/kolla/certificates``.

The certificates must be valid for the IP address of the host running RabbitMQ
on the API network.

Additional TLS configuration options may be passed to RabbitMQ via
``rabbitmq_tls_options``. This should be a dict, and the keys will be prefixed
with ``ssl_options.``. For example:

.. code-block:: yaml

   rabbitmq_tls_options:
     ciphers.1: ECDHE-ECDSA-AES256-GCM-SHA384
     ciphers.2: ECDHE-RSA-AES256-GCM-SHA384
     ciphers.3: ECDHE-ECDSA-AES256-SHA384
     honor_cipher_order: true
     honor_ecc_order: true

Details on configuration of RabbitMQ for TLS can be found in the `RabbitMQ
documentation <https://www.rabbitmq.com/ssl.html>`__.

When ``om_rabbitmq_enable_tls`` is ``true`` (it defaults to the value of
``rabbitmq_enable_tls``), applicable OpenStack services will be configured to
use oslo.messaging with TLS enabled. The CA certificate is configured via
``om_rabbitmq_cacert`` (it defaults to ``rabbitmq_cacert``, which points to the
system's trusted CA certificate bundle for TLS). Note that there is currently
no support for using client certificates.

For testing purposes, Kolla Ansible provides the ``kolla-ansible certificates``
command, which will generate self-signed certificates for RabbitMQ if
``rabbitmq_enable_tls`` is ``true``.

Management API and UI
---------------------

The management API and UI are accessed via HAProxy, exposed only on the
internal VIP. As such, traffic to this endpoint is encrypted when
``kolla_enable_tls_internal`` is ``true``. See :ref:`tls-configuration`.

Passing arguments to RabbitMQ server's Erlang VM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Erlang programs run in an Erlang VM (virtual machine) and use the Erlang
runtime.  The Erlang VM can be configured.

Kolla Ansible makes it possible to pass arguments to the Erlang VM via the
usage of the ``rabbitmq_server_additional_erl_args`` variable. The contents of
it are appended to the ``RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS`` environment
variable which is passed to the RabbitMQ server startup script. Kolla Ansible
already configures RabbitMQ server for IPv6 (if necessary). Any argument can be
passed there as documented in https://www.rabbitmq.com/runtime.html

The default value for ``rabbitmq_server_additional_erl_args`` is ``+S 2:2 +sbwt
none +sbwtdcpu none +sbwtdio none``.

By default RabbitMQ starts N schedulers where N is the number of CPU cores,
including hyper-threaded cores. This is fine when you assume all CPUs are
dedicated to RabbitMQ. Its not a good idea in a typical Kolla Ansible setup.
Here we go for two scheduler threads (``+S 2:2``).  More details can be found
here: https://www.rabbitmq.com/runtime.html#scheduling and here:
https://erlang.org/doc/man/erl.html#emulator-flags

The ``+sbwt none +sbwtdcpu none +sbwtdio none`` arguments prevent busy waiting
of the scheduler, for more details see:
https://www.rabbitmq.com/runtime.html#busy-waiting.

High Availability
~~~~~~~~~~~~~~~~~

With the release of RabbitMQ 4.0, all queues are highly available as they are
configured to be quorum queues by default. RabbitMQ also offer queues called
streams, which can be used to replace "fanout" queues with a more performant
alternative. This is enabled by default, but can be disabled by setting
``om_enable_rabbitmq_stream_fanout: false``. When changing queues to a
different type, the follow procedure will be needed.

.. warning::

   Since the default changed to have all queues be of durable type in the Epoxy
   release, following procedure is required to be carried out before any
   upgrade to Epoxy.

1. Generate the new config for all services. After this, make sure not to
   restart any containers until after the RabbitMQ state has been reset.

   .. code-block:: console

      kolla-ansible genconfig

2. Stop all OpenStack services which use RabbitMQ, so that they will not
   attempt to recreate any queues yet.

   .. code-block:: console

      kolla-ansible stop --tags <service-tags>

3. Reconfigure RabbitMQ if you were previously using
   ``om_enable_rabbitmq_high_availability``.

   .. code-block:: console

      kolla-ansible reconfigure --tags rabbitmq

4. Reset the state on each RabbitMQ, to remove the old transient queues and
   exchanges.

   .. code-block:: console

      kolla-ansible rabbitmq-reset-state

5. Start the OpenStack services again, at which point they will recreate the
   appropriate queues as durable.

   .. code-block:: console

      kolla-ansible deploy --tags <service-tags>


Upgrading RabbitMQ
~~~~~~~~~~~~~~~~~~

RabbitMQ upgrades in Kolla Ansible are typically restricted to a single minor
version increment at a time (e.g., from 4.0.x to 4.1.x). This is a safety
measure to ensure that RabbitMQ's internal data migrations and feature flags
are processed correctly.

In some cases, specific multi-version upgrade paths are supported (for example,
jumping from 3.13 directly to 4.2). These allowed paths are defined
using the ``rabbitmq_allowed_upgrades`` variable in the RabbitMQ role defaults.

Operators can customize or extend these allowed upgrade paths by overriding
this variable in ``globals.yml``.

.. code-block:: yaml

   rabbitmq_allowed_upgrades:
     "3.13":
       - "4.0"
       - "4.1"
       - "4.2"
     "4.0":
       - "4.1"
       - "4.2"

If an invalid upgrade path is detected, the deployment will fail with a
descriptive error message during the ``rabbitmq-version-check`` task,
suggesting the next appropriate intermediate version.

Handling Stream Replicas
~~~~~~~~~~~~~~~~~~~~~~~~

RabbitMQ streams are expected to be replicated across the nodes in the
cluster. However, RabbitMQ itself will only create replicas of a stream when
the stream is initially declared. This means that any streams declared when a
RabbitMQ node is out of service must be explicitly managed by an operator.
RabbitMQ documents how to manage stream replicas here:
https://www.rabbitmq.com/docs/streams#member-management

An example script to create any missing stream replicas can be found under
`kolla-ansible/contrib/ops/rabbitmq/rabbitmq-repair-stream-replicas.sh
<https://opendev.org/openstack/kolla-ansible/src/branch/master/contrib/ops/rabbitmq/rabbitmq-repair-stream-replicas.sh>`__.
This should be executed from a host running the RabbitMQ container.
Currently, membership changes for streams `is not entirely safe
<https://github.com/rabbitmq/rabbitmq-server/discussions/14246>`__, so this
script should only be used when the RabbitMQ cluster is in a known healthy
state.

Streams Retention Period
~~~~~~~~~~~~~~~~~~~~~~~~

When using RabbitMQ streams for fanout queues by setting
``om_enable_rabbitmq_stream_fanout: true``, users can set retention policy for
them with the use of two variables ``rabbitmq_stream_max_segment_size_bytes``
and ``rabbitmq_stream_segment_max_age`` to avoid running out of disk space
eventually.

Default configuration set segments of a stream queues to have maximum size of
500 MB (`RabbitMQ default <https://www.rabbitmq.com/docs/streams#declaring>`__)
and the retention time of 1800 seconds once a segment reaches the maximum size
(`oslo.messaging default
<https://docs.openstack.org/oslo.messaging/latest/configuration/opts.html#oslo_messaging_rabbit.rabbit_transient_queues_ttl>`__).
These default values will leave large number of ready messages in stream
queues even though old ones are removed by the retention policy.
So it is recommended to tune them based on how busy the cloud is.

``rabbitmq_stream_max_segment_size_bytes`` sets the maximum size of stream
segments. This variable needs to be positive integer.

``rabbitmq_stream_segment_max_age`` sets the retention time of segments that
reached the maximum size. This variable needs to be string with valid options
of Y, M, D, h, m, s (e.g. 24h for 24 hours).

.. code-block:: yaml

   # Example custom retention policy configuration
   rabbitmq_stream_max_segment_size_bytes: 5000 # 5 KB
   rabbitmq_stream_segment_max_age: "60s" # 60 seconds
