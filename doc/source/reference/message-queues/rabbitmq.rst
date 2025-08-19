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
* RabbitMQ Management API and UI (backend connection from HAProxy to RabbitMQ)

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
