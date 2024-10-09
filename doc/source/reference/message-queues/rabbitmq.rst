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

RabbitMQ offers two options to configure HA:
  * Quorum queues (enabled by default and controlled by
    ``om_enable_rabbitmq_quorum_queues`` variable)
  * Classic queue mirroring and durable queues (deprecated in RabbitMQ and to
    be dropped in 4.0, controlled by ``om_enable_rabbitmq_high_availability``)

There are some queue types which are intentionally not mirrored
using the exclusionary pattern ``^(?!(amq\\.)|(.*_fanout_)|(reply_)).*``.

After enabling one of these values on a running system, there are some
additional steps needed to migrate from transient to durable queues.

.. warning::

   If you choose to enable quorum queues on an existing RabbitMQ cluster,
   the following procedure is required to be carried out before an upgrade.

   Notice, that the default will be changed from non-HA to Quorum queues in the
   Bobcat release. This means that you will also need to perform this migration
   before a SLURP upgrade to Caracal.

1. Stop all OpenStack services which use RabbitMQ, so that they will not
   attempt to recreate any queues yet.

   .. code-block:: console

      kolla-ansible stop --tags <service-tags>

2. Generate the new config for all services.

   .. code-block:: console

      kolla-ansible genconfig

3. Reconfigure RabbitMQ if you are using
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

SLURP
~~~~~

RabbitMQ has two major version releases per year but does not support jumping
two versions in one upgrade. So if you want to perform a skip-level upgrade,
you must first upgrade RabbitMQ to an intermediary version. To do this, Kolla
provides multiple RabbitMQ versions in the odd OpenStack releases. To use the
upgrade from Antelope to Caracal as an example, we start on RabbitMQ version
3.11. In Antelope, you should upgrade to RabbitMQ version 3.12 with the command
below. You can then proceed with the usual SLURP upgrade to Caracal (and
therefore RabbitMQ version 3.13).

.. warning::

   This command should be run from the Antelope release.

   Note that this command is NOT idempotent. See "RabbitMQ versions" below for
   an alternative approach.

.. code-block:: console

   kolla-ansible rabbitmq-upgrade 3.12

RabbitMQ versions
~~~~~~~~~~~~~~~~~

Alternatively, you can set ``rabbitmq_image`` in your configuration
``globals.yml`` for idempotence in deployments. As an example, Kolla ships
versions 3.11, 3.12 and 3.13 of RabbitMQ in Antelope. By default, Antelope
Kolla-Ansible will deploy version 3.11. If you wish to deploy a later version,
you must override the image. if you want to use version 3.12 change
``rabbitmq_image`` in ``globals.yml`` as follows:

.. code-block:: yaml

   rabbitmq_image: "{{ docker_registry ~ '/' if docker_registry else '' }}{{ docker_namespace }}/rabbitmq-3-12"

You can then upgrade RabbitMQ with the usual command:

.. code-block:: console

   kolla-ansible upgrade --tags rabbitmq

Note again that RabbitMQ does not support upgrades between more than one major
version, so if you wish to upgrade to version 3.13 you must first upgrade to
3.12.
