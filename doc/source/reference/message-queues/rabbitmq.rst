.. _rabbitmq:

========
RabbitMQ
========

RabbitMQ is a message broker written in Erlang.
It is currently the default provider of message queues in Kolla Ansible
deployments.

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
