.. _security:

==============
Kolla Security
==============

Non Root containers
~~~~~~~~~~~~~~~~~~~

The OpenStack services, with a few exceptions, run as non root inside
of Kolla's containers. Kolla uses the Docker provided ``USER`` flag to
set the appropriate user for each service.

SELinux
~~~~~~~

The state of SELinux in Kolla is a work in progress. The short answer
is you must disable it until selinux polices are written for the
Docker containers.

To understand why Kolla needs to set certain selinux policies for
services that you wouldn't expect to need them (rabbitmq, mariadb, glance
and so on) we must take a step back and talk about Docker.

Docker has not had the concept of persistent containerized data until
recently. This means when a container is run the data it creates is
destroyed when the container goes away, which is obviously no good
in the case of upgrades.

It was suggested data containers could solve this issue by only holding
data if they were never recreated, leading to a scary state where you
could lose access to your data if the wrong command was executed. The
real answer to this problem came in Docker 1.9 with the introduction of
named volumes. You could now address volumes directly by name removing
the need for so called **data containers** all together.

Another solution to the persistent data issue is to use a host bind
mount which involves making, for sake of example, host directory
``var/lib/mysql`` available inside the container at ``var/lib/mysql``.
This absolutely solves the problem of persistent data, but it introduces
another security issue, permissions. With this host bind mount solution
the data in ``var/lib/mysql`` will be owned by the mysql user in the
container. Unfortunately, that mysql user in the container could have
any UID/GID and that's who will own the data outside the container
introducing a potential security risk. Additionally, this method
dirties the host and requires host permissions to the directories
to bind mount.

The solution Kolla chose is named volumes.

Why does this matter in the case of selinux? Kolla does not run the
process. It is launching as root in most cases. So glance-api is run
as the glance user, and mariadb is run as the mysql user, and so on.
When mounting a named volume in the location that the persistent data
will be stored it will be owned by the root user and group. The mysql
user has no permissions to write to this folder now. What Kolla does
is allow a select few commands to be run with sudo as the mysql user.
This allows the mysql user to chown a specific, explicit directory
and store its data in a named volume without the security risk and
other downsides of host bind mounts. The downside to this is selinux
blocks those sudo commands and it will do so until we make explicit
policies to allow those operations.

Kolla-ansible users
===================

Prior to Queens, when users want to connect using non-root user, they must add
extra option ``ansible_become=True`` which is inconvenient and add security
risk. In Queens, almost all services have support for escalation for only
necessary tasks. In Rocky, all services have this capability, so users do not
need to add ``ansible_become`` option if connection user has passwordless sudo
capability.

Prior to Rocky, ``ansible_user`` (the user which Ansible uses to connect
via SSH) is default configuration owner and group in target nodes.
From Rocky release, Kolla support connection using any user which has
passwordless sudo capability. For setting custom owner user and group, user
can set ``config_owner_user`` and ``config_owner_group`` in ``globals.yml``.

FirewallD
~~~~~~~~~
Prior to Zed, Kolla Ansible would disable any system firewall leaving
configuration up to the end users. Firewalld is now supported and will
configure external api ports for each enabled OpenStack service.

The following variables should be configured in Kolla Ansible's
``globals.yml``

* external_api_firewalld_zone
    * The default zone to configure ports on for external API Access
    * String - defaults to the public zone
* enable_external_api_firewalld
    * Setting to true will enable external API ports configuration
    * Bool - set to true or false
* disable_firewall
    * Setting to false will stop Kolla Ansible
      from disabling the systems firewall
    * Bool - set to true or false


Prerequisites
=============
Firewalld needs to be installed beforehand.

Kayobe can be used to automate the installation and configuration of firewalld
before running Kolla Ansible. If you do not use Kayobe you must ensure that
that firewalld has been installed and setup correctly.

You can check the current active zones by running the command below.
If the output of the command is blank then no zones are configured as active.

.. code-block:: console

   sudo firewall-cmd --get-active-zones

You should ensure that the system is reachable via SSH to avoid lockout,
to add ssh to a particular zone run the following command.

.. code-block:: console

   sudo firewall-cmd --permanent --zone=<zone>  --add-service=ssh

You should also set the required interface on a particular zone by running the
below command. This will mark the zone as active on the specified interface.

.. code-block:: console

   sudo firewall-cmd --permanent --zone=<zone> --change-interface=<interface>

if more than one interface is required on a specific zone this can be achieved
by running

.. code-block:: console

   sudo firewall-cmd --permanent --zone=public --add-interface=<additional interface>

Any other ports that need to be opened on the system should be done
before hand. The following command will add additional ports to a zone

.. code-block:: console

   sudo firewall-cmd --zone=public --add-port=8080/tcp --permanent

Dependent on your infrastructure security policy you may wish to add a policy
of drop on the public zone this can be achieved by running the following
command.

.. code-block:: console

   sudo firewall-cmd --permanent --set-target=DROP --zone=public

To apply changes to the system firewall run

.. code-block:: console

   sudo firewalld-cmd --reload

For additional information and configuration please see:
https://firewalld.org/documentation/man-pages/firewall-cmd.html
