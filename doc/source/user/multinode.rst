.. _multinode:

=============================
Multinode Deployment of Kolla
=============================

.. _deploy_a_registry:

Deploy a registry
=================

A Docker registry is a locally-hosted registry that replaces the need to pull
from a public registry to get images. Kolla can function with or without
a local registry, however for a multinode deployment some type of local
registry is recommended. Only one registry instance needs to be deployed,
although HA features exist for registry services.

A very simple registry may be deployed on the current host as follows:

.. code-block:: console

   docker run -d \
    --network host \
    --name registry \
    --restart=always \
    -e REGISTRY_HTTP_ADDR=0.0.0.0:4000 \
    -v registry:/var/lib/registry \
    registry:2

Here we are using port 4000 to avoid a conflict with Keystone. If the registry
is not running on the same host as Keystone, the ``-e`` argument may be
omitted.

Edit ``globals.yml`` and add the following, where ``192.168.1.100:4000`` is the
IP address and port on which the registry is listening:

.. code-block:: yaml

   docker_registry: 192.168.1.100:4000
   docker_registry_insecure: yes

.. _edit-inventory:

Edit the Inventory File
=======================

The ansible inventory file contains all the information needed to determine
what services will land on which hosts. Edit the inventory file in the
Kolla Ansible directory ``ansible/inventory/multinode``. If Kolla Ansible
was installed with pip, it can be found in ``/usr/share/kolla-ansible``.

Add the IP addresses or hostnames to a group and the services associated with
that group will land on that host. IP addresses or hostnames must be added to
the groups control, network, compute, monitoring and storage. Also, define
additional behavioral inventory parameters such as ``ansible_ssh_user``,
``ansible_become`` and ``ansible_private_key_file/ansible_ssh_pass`` which
controls how ansible interacts with remote hosts.

.. note::

   Ansible uses SSH to connect the deployment host and target hosts. For more
   information about SSH authentication please reference
   `Ansible documentation <http://docs.ansible.com/ansible/latest/intro_inventory.html>`__.

.. code-block:: ini

   # These initial groups are the only groups required to be modified. The
   # additional groups are for more control of the environment.
   [control]
   # These hostname must be resolvable from your deployment host
   control01      ansible_ssh_user=<ssh-username> ansible_become=True ansible_private_key_file=<path/to/private-key-file>
   192.168.122.24 ansible_ssh_user=<ssh-username> ansible_become=True ansible_private_key_file=<path/to/private-key-file>

.. note::

   Additional inventory parameters might be required according to your
   environment setup. Reference `Ansible Documentation
   <http://docs.ansible.com/ansible/latest/intro_inventory.html>`__ for more
   information.


For more advanced roles, the operator can edit which services will be
associated in with each group. Keep in mind that some services have to be
grouped together and changing these around can break your deployment:

.. code-block:: ini

   [kibana:children]
   control

   [elasticsearch:children]
   control

   [loadbalancer:children]
   network

.. _multinode-host-and-group-variables:

Host and group variables
========================

Typically, Kolla Ansible configuration is stored in the ``globals.yml`` file.
Variables in this file apply to all hosts. In an environment with multiple
hosts, it may become necessary to have different values for variables for
different hosts. A common example of this is for network interface
configuration, e.g. ``api_interface``.

Ansible's host and group variables can be assigned in a `variety of ways
<https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html>`_.
Simplest is in the inventory file itself:

.. code-block:: ini

   # Host with a host variable.
   [control]
   control01 api_interface=eth3

   # Group with a group variable.
   [control:vars]
   api_interface=eth4

This can quickly start to become difficult to maintain, so it may be preferable
to use ``host_vars`` or ``group_vars`` directories containing YAML files with
host or group variables:

.. code-block:: console

   inventory/
     group_vars/
       control
     host_vars/
       control01
     multinode

`Ansible's variable precedence rules
<https://docs.ansible.com/ansible/latest/user_guide/playbooks_variables.html#ansible-variable-precedence>`__
are quite complex, but it is worth becoming familiar with them if using host
and group variables. The playbook group variables in
``ansible/group_vars/all/`` define global defaults, and these take
precedence over variables defined in an inventory file and inventory
``group_vars/all``, but not over inventory ``group_vars/*``. Variables in
'extra' files (``globals.yml``) have the highest precedence, so any variables
which must differ between hosts must not be in ``globals.yml``.

Deploying Kolla
===============

.. note::

    If there are multiple keepalived clusters running within the same layer 2
    network, edit the file ``/etc/kolla/globals.yml`` and specify a
    ``keepalived_virtual_router_id``. The ``keepalived_virtual_router_id`` should
    be unique and belong to the range 0 to 255.

.. note::

   If glance is configured to use ``file`` as backend, only one ``glance_api``
   container will be started. ``file`` is enabled by default when no other
   backend is specified in ``/etc/kolla/globals.yml``.

First, check that the deployment targets are in a state where Kolla may deploy
to them:

.. code-block:: console

   kolla-ansible prechecks -i <path/to/multinode/inventory/file>

.. note::

   RabbitMQ doesn't work with IP addresses, hence the IP address of
   ``api_interface`` should be resolvable by hostnames to make sure that all
   RabbitMQ Cluster hosts can resolve each others hostnames beforehand.

Run the deployment:

.. code-block:: console

   kolla-ansible deploy -i <path/to/multinode/inventory/file>

Validate generated configuration files of enabled services:

.. code-block:: console

   kolla-ansible validate-config -i <path/to/multinode/inventory/file>

.. note::

   Due to the nature of the configuration generation the validation can
   currently only be done after the first deployment. For some validations
   it is necessary to access the running containers.
   The validation tasks can be found - and altered - in each ansible role under
   ``kolla-ansible/ansible/roles/$role/tasks/config_validate.yml``.
   The validation for most openstack services is done by the special role:
   ``service-config-validate``.

