.. _external-mariadb-guide:

================
External MariaDB
================

Sometimes, for various reasons (Redundancy, organisational policies, etc.),
it might be necessary to use an externally managed database.
This use case can be achieved by simply taking some extra steps:

Requirements
~~~~~~~~~~~~

* An existing MariaDB cluster / server, reachable from all of your
  nodes.
* If you choose to use preconfigured databases and users
  (**use_preconfigured_databases** is set to "yes"), databases and
  user accounts for all enabled services should exist on the
  database.
* If you choose not to use preconfigured databases and users
  (**use_preconfigured_databases** is set to "no"), root access to
  the database must be available in order to configure databases and
  user accounts for all enabled services.

Enabling External MariaDB support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to enable external mariadb support,
you will first need to disable mariadb deployment,
by ensuring the following line exists within ``/etc/kolla/globals.yml`` :

.. code-block:: yaml

   enable_mariadb: "no"

There are two ways in which you can use external MariaDB:
* Using an already load-balanced MariaDB address
* Using an external MariaDB cluster

Using an already load-balanced MariaDB address (recommended)
------------------------------------------------------------

If your external database already has a load balancer, you will
need to do the following:

#. Edit the inventory file, change ``control`` to the hostname of the load
   balancer within the ``mariadb`` group as below:

   .. code-block:: ini

      [mariadb]
      myexternalmariadbloadbalancer.com


#. Define ``database_address`` in ``/etc/kolla/globals.yml`` file:

   .. code-block:: yaml

      database_address: myexternalmariadbloadbalancer.com

.. note::

   If ``enable_external_mariadb_load_balancer`` is set to ``no``
   (default), the external DB load balancer should be accessible
   from all nodes during your deployment.

Using an external MariaDB cluster
---------------------------------

Using this way, you need to adjust the inventory file:

.. code-block:: ini

   [mariadb:children]
   myexternaldbserver1.com
   myexternaldbserver2.com
   myexternaldbserver3.com

If you choose to use haproxy for load balancing between the
members of the cluster, every node within this group
needs to be resolvable and reachable from all
the hosts within the ``[loadbalancer:children]``  group
of your inventory (defaults to ``[network]``).

In addition, configure the ``/etc/kolla/globals.yml`` file
according to the following configuration:

.. code-block:: yaml

   enable_external_mariadb_load_balancer: yes

Using External MariaDB with a privileged user
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In case your MariaDB user is root, just leave
everything as it is within globals.yml (Except the
internal mariadb deployment, which should be disabled),
and set the ``database_password`` in ``/etc/kolla/passwords.yml`` file:

.. code-block:: yaml

   database_password: mySuperSecurePassword

If the MariaDB ``username`` is not ``root``, set ``database_user`` in
``/etc/kolla/globals.yml`` file:

.. code-block:: yaml

   database_user: "privillegeduser"

Using preconfigured databases / users:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first step you need to take is to set ``use_preconfigured_databases`` to
``yes`` in the ``/etc/kolla/globals.yml`` file:

.. code-block:: yaml

   use_preconfigured_databases: "yes"

.. note::

   when the ``use_preconfigured_databases`` flag is set to ``"yes"``, you need
   to make sure the mysql variable ``log_bin_trust_function_creators``
   set to ``1`` by the database administrator before running the
   :command:`upgrade` command.

Using External MariaDB with separated, preconfigured users and databases
------------------------------------------------------------------------

In order to achieve this, you will need to define the user names in the
``/etc/kolla/globals.yml`` file, as illustrated by the example below:


.. code-block:: yaml

   keystone_database_user: preconfigureduser1
   nova_database_user: preconfigureduser2

Also, you will need to set the passwords for all databases in the
``/etc/kolla/passwords.yml`` file

However, fortunately, using a common user across all databases is possible.

Using External MariaDB with a common user across databases
----------------------------------------------------------

In order to use a common, preconfigured user across all databases,
all you need to do is the following steps:

#. Edit the ``/etc/kolla/globals.yml`` file, add the following:

   .. code-block:: yaml

      use_common_mariadb_user: "yes"

#. Set the database_user within ``/etc/kolla/globals.yml`` to
   the one provided to you:

   .. code-block:: yaml

      database_user: mycommondatabaseuser

#. Set the common password for all components within
   ``/etc/kolla/passwords.yml``. In order to achieve that you
   could use the following command:

   .. code-block:: console

      sed -i -r -e 's/([a-z_]{0,}database_password:+)(.*)$/\1 mycommonpass/gi' /etc/kolla/passwords.yml

