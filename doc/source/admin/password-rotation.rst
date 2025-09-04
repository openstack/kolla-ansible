=================
Password Rotation
=================

This guide describes how to change the internal secrets from ``passwords.yml``
used by Kolla-Ansible. It does not cover every possible ``passwords.yml``
variable, only the most common ones.

.. warning::

   Always back up your ``passwords.yml`` file before making any changes.
   Otherwise, it is easy to make unrecoverable mistakes.

.. warning::

   This guide relies on recent changes to Kolla and Kolla-Ansible. You may
   encounter errors if applying this guide to older deployments. It is
   recommended that you update your containers and kolla-ansible to the latest
   available versions before proceeding.

Regenerating secrets
--------------------

Passwords can be quickly re-generated using ``kolla-genpwd``.

Assuming an existing ``/etc/kolla/passwords.yml`` file, make a backup:

.. code-block:: bash

   cp /etc/kolla/passwords.yml ./passwords.yml.bak

Edit the ``passwords.yml`` file to remove the password strings for any secrets
that need to be regenerated i.e. change ``foo: "bar"`` to ``foo:``.

Regenerate the removed passwords:

.. code-block:: bash

   kolla-genpwd -p /etc/kolla/passwords.yml

Applying regenerated secrets
----------------------------

The majority of the secrets can be applied by simply reconfiguring services
with ``kolla-ansible reconfigure``. Below is a list of secrets that can be
applied this way.


* ``*_keystone_password``
* ``*_database_password`` (excluding ``nova_database_password``)
* ``*_ssh_key`` (excluding ``kolla_ssh_key``)
* ``keystone_admin_password``
* ``designate_rndc_key``
* ``keepalived_password``
* ``libvirt_sasl_password``
* ``metadata_secret``
* ``opensearch_dashboards_password``
* ``osprofiler_secret``
* ``prometheus_alertmanager_password``
* ``qdrouterd_password``
* ``valkey_master_password``

It is possible to change more secrets however some require manual steps. The
manual steps vary depending on the secret. They are listed below in the order
they should be applied if they are to be changed at the same time. Once all
manual steps are complete, reconfigure services (``kolla-ansible
reconfigure``).

For simplicity, this guide assumes Docker is being used. The same commands
should also work for Podman deployments by replacing instances of ``docker``
with ``podman`` in all relevant commands.

Kolla SSH key
^^^^^^^^^^^^^
There is currently no mechanism within Kolla-Ansible to rotate
``kolla_ssh_key``. It is however a relatively simple task to perform using a
standard Ansible playbook, or can be performed by hand on smaller deployments.

Horizon Secret Key
^^^^^^^^^^^^^^^^^^
The Horizon secret key (``horizon_secret_key``) is unique because it explicitly
supports rotation. In reality, it is a Django secret key, and is used for
cryptographic signing e.g. generating password recovery links. To minimise user
impact, it is possible to set two secret keys at once. The new one will be used
for generating new artifacts, while the old one will still be accepted for
existing artifacts.

Take note of the old password, generate a new one, and take note of it as well.

Add it to the ``passwords.yml`` file, along with the old secret, in this
exact format (including quotes in the middle):

.. code:: bash

   horizon_secret_key: newsecret' 'oldsecret

It is important to remember to remove the old key and reconfigure services
again, after all old artifacts have expired e.g. after approximately one to two
weeks.

Grafana Admin Password
^^^^^^^^^^^^^^^^^^^^^^
The Grafana admin password (``grafana_admin_password``) must be rotated
manually.

#. Generate a new Grafana Admin password.

#. Replace the old password in ``passwords.yml``.

#. Exec into any Grafana container:

   .. code:: bash

      docker exec -it grafana bash

#. Run the password reset command, then enter the new password:

   .. code:: bash

      grafana-cli admin reset-admin-password --password-from-stdin

Database Password
^^^^^^^^^^^^^^^^^
The database administrator password (``database_password``) must be rotated
manually.

#. Generate a new database password.

#. Replace the old password in ``passwords.yml``, take note of both the old and
   new passwords.

#. SSH to a host running a MariaDB container.

#. Exec into the MariaDB container:

   .. code-block:: bash

      docker exec -it mariadb bash

#. Log in to the database. You will be prompted for the password. Use the
   old value of ``database_password``:

   .. code:: bash

      mysql --batch -uroot -p

#. Check the current state of the ``root`` user:

   .. code:: bash

      SELECT Host,User,Password FROM mysql.user WHERE User='root';

#. Update the password for the ``root`` user:

   .. code:: bash

      SET PASSWORD FOR 'root'@'%' = PASSWORD('newpassword');

#. Check that the password hash has changed in the user list:

   .. code:: bash

      SELECT Host,User,Password FROM mysql.user WHERE User='root';

#. If there are any remaining root users with the old password e.g.
   ``root@localhost``, change the password for them too.

Nova Database Password
^^^^^^^^^^^^^^^^^^^^^^
The nova database admin user password (``nova_database_password``) must be
rotated manually.

.. warning::

   From this point onward, API service may be disrupted.

#. Generate a new Nova database password.

#. Replace the old password in ``passwords.yml``.

#. Exec into the ``nova_conductor`` container:

   .. code:: bash

      docker exec -it nova_conductor bash

#. List the cells:

   .. code:: bash

      nova-manage cell_v2 list_cells --verbose

#. Find the entry for ``cell0``, copy the Database Connection value,
   replace the password in the string with the new value, and update it
   with the following command:

   .. code:: bash

      nova-manage cell_v2 update_cell --cell_uuid 00000000-0000-0000-0000-000000000000 --database_connection "CONNECTION WITH NEW PASSWORD HERE" --transport-url "none:///"

   (If the ``cell_uuid`` for ``cell0`` is not
   ``00000000-0000-0000-0000-000000000000``, change the above command
   accordingly)

Heat Domain Admin Password
^^^^^^^^^^^^^^^^^^^^^^^^^^
The keystone password for the heat domain admin service user
(``heat_domain_admin_password``) must be rotated manually.

It can be changed by an administrator just like any other standard OpenStack
user password. Generate a new password, replace the old password in
``passwords.yml``, then apply the change manually:

.. code-block:: bash

   openstack user set --password <password> heat_domain_admin --domain heat_user_domain

RabbitMQ Secrets
^^^^^^^^^^^^^^^^
RabbitMQ uses two main secrets. An Erlang cookie for cluster membership
(``rabbitmq_cluster_cookie``), and a RabbitMQ management user password
(``rabbitmq_password``). There is currently no documented process for
seamlessly rotating these secrets. Many OpenStack services use RabbitMQ for
communication and reconfiguring them with the new credentials can take some
time, resulting in a relatively long API outage.

It is recommended that you stop all services, then stop and destroy the
RabbitMQ containers and volumes. Because the RabbitMQ containers are destroyed,
``kolla-ansible deploy`` should be used to restart services rather than
``kolla-ansible reconfigure``. Detailed steps are listed below:

#. Generate a new ``rabbitmq_cluster_cookie`` and ``rabbitmq_password``.

#. Replace the old values in ``passwords.yml``.

#. Stop OpenStack services:

   .. code-block:: bash

      kolla-ansible stop -i inventory

#. On each node running RabbitMQ, destroy its containers and volumes:

   .. code-block:: bash

      docker stop rabbitmq
      docker rm rabbitmq
      docker volume rm rabbitmq

#. Redeploy services:

   .. code-block:: bash

      kolla-ansible deploy -i inventory

Post-redeploy changes
^^^^^^^^^^^^^^^^^^^^^
Once services have been redeployed, the existing Memcached data should be
flushed. The old Memcached password will no longer be used so any data stored
using it will be inaccessible.

The instructions below must be run from a host that has access to the network
the Memcached containers are using. If you are not sure, run them from a host
that is running Memcached.

#. Install a telnet client:

   .. code-block:: bash

      apt/dnf install telnet

#. Check the config for the IP and port used by Memcached (on every host
   running Memcached):

   .. code:: bash

      sudo grep command /etc/kolla/memcached/config.json

   The IP and port will be printed after ``-l`` and ``-p`` respectively

#. For each container start a Telnet session, clear all data, then
   exit:

   .. code:: bash

      telnet <ip> <port>
      flush_all
      quit

Known out-of-scope secrets
--------------------------
Below is a list of passwords that are known to be outside the scope of this
guide.

* ``docker_registry_password`` - kolla-ansible cannot manage docker registries.
