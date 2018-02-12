.. _external-mariadb-guide:

================
External MariaDB
================

Sometimes, for various reasons (Redundancy, organisational policies, etc.),
it might be necessary to use an externally managed database.
This use case can be achieved by simply taking some extra steps:

Requirements
============

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
=================================

In order to enable external mariadb support,
you will first need to disable mariadb deployment,
by ensuring the following line exists within ``/etc/kolla/globals.yml`` :

.. code-block:: yaml

  enable_mariadb: "no"

.. end

There are two ways in which you can use
external MariaDB:

Using an already load-balanced MariaDB address (recommended)
------------------------------------------------------------

If your external database already has a
load balancer, you will need to do the following:

* Within your inventory file, just add the hostname
  of the load balancer within the mariadb group,
  described as below:

Change the following

.. code-block:: ini

  [mariadb:children]
  control

.. end

so that it looks like below:

.. code-block:: ini

  [mariadb]
  myexternalmariadbloadbalancer.com

.. end

* Define **database_address** within ``/etc/kolla/globals.yml``

.. code-block:: yaml

  database_address: myexternalloadbalancer.com

.. end

Please note that if **enable_external_mariadb_load_balancer** is
set to "no" - **default**, the external DB load balancer will need to be
accessible from all nodes within your deployment, which might
connect to it.

Using an external MariaDB cluster:
----------------------------------

Then, you will need to adjust your inventory file:

Change the following

.. code-block:: ini

  [mariadb:children]
  control

.. end

so that it looks like below:

.. code-block:: ini

  [mariadb]
  myexternaldbserver1.com
  myexternaldbserver2.com
  myexternaldbserver3.com

.. end

If you choose to use haproxy for load balancing between the
members of the cluster, every node within this group
needs to be resolvable and reachable and resolvable from all
the hosts within the **[haproxy:children]**  group
of your inventory (defaults to **[network]**).

In addition to that, you also need to set the following within
``/etc/kolla/globals.yml``:

.. code-block:: yaml

  enable_external_mariadb_load_balancer: yes

.. end

Using External MariaDB with a privileged user
=============================================

In case your MariaDB user is root, just leave
everything as it is within globals.yml (Except the
internal mariadb deployment, which should be disabled),
and set the **database_password** field within
``/etc/kolla/passwords.yml``

.. code-block:: yaml

  database_password: mySuperSecurePassword

.. end

In case your username is other than **root**, you will
need to also set it, within ``/etc/kolla/globals.yml``

.. code-block:: yaml

  database_username: "privillegeduser"

.. end

Using preconfigured databases / users:
======================================

The first step you need to take is the following:

Within ``/etc/kolla/globals.yml``, set the following:

.. code-block:: yaml

  use_preconfigured_databases: "yes"

.. end

.. note:: Please note that when the ``use_preconfigured_databases`` flag
  is set to ``"yes"``, you need to have the ``log_bin_trust_function_creators``
  mysql variable set to ``1`` by your database administrator before running the
  ``upgrade`` command.

Using External MariaDB with separated, preconfigured users and databases
------------------------------------------------------------------------

In order to achieve this, you will need to define the user names within
``/etc/kolla/globals.yml``, as illustrated by the example below:


.. code-block:: yaml

  keystone_database_user: preconfigureduser1
  nova_database_user: preconfigureduser2

.. end

You will need to also set the passwords for all databases within
``/etc/kolla/passwords.yml``


However, fortunately, using a common user across
all databases is also possible.


Using External MariaDB with a common user across databases
----------------------------------------------------------

In order to use a common, preconfigured user across all databases,
all you need to do is the following:

* Within ``/etc/kolla/globals.yml``, add the following:

.. code-block:: yaml

  use_common_mariadb_user: "yes"

.. end

* Set the database_user within ``/etc/kolla/globals.yml`` to
  the one provided to you:

.. code-block:: yaml

  database_user: mycommondatabaseuser

.. end

* Set the common password for all components within ``/etc/kolla/passwords.yml```.
  In order to achieve that you could use the following command:

.. code-block:: console

  sed -i -r -e 's/([a-z_]{0,}database_password:+)(.*)$/\1 mycommonpass/gi' /etc/kolla/passwords.yml

.. end