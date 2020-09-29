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

Erlang programs run in Erlang VM (virtual machine) and use Erlang runtime.
Erlang VM can be configured.

Kolla Ansible makes it possible to pass arguments to the Erlang VM via the
usage of ``rabbitmq_server_additional_erl_args`` variable. The contents of it
are appended to ``RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS`` environment variable
passed to RabbitMQ server startup script. Kolla Ansible already configures
RabbitMQ server for IPv6 (if necessary). Any argument can be passed there as
documented in https://www.rabbitmq.com/runtime.html
