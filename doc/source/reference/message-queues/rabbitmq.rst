.. _rabbitmq:

========
RabbitMQ
========

RabbitMQ is a message broker written in Erlang.
It is currently the default provider of message queues in Kolla Ansible
deployments.

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
