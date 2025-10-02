====================
Adding a new service
====================

When adding a role for a new service in Ansible, there are couple of patterns
which Kolla uses throughout and which should be followed.

* The sample inventories

  Entries should be added for the service in each of
  ``ansible/inventory/multinode`` and ``ansible/inventory/all-in-one``.

* The playbook

  The main playbook that ties all roles together is in ``ansible/site.yml``,
  this should be updated with appropriate roles, tags, and conditions. Ensure
  also that supporting hosts such as haproxy are updated when necessary.

* The common role

  A ``common`` role exists which sets up logging, ``kolla-toolbox`` and other
  supporting components. This should be included in all services within
  ``meta/main.yml`` of your role.

* Common tasks

  All services should include the following tasks:

  - ``deploy.yml`` : Used to bootstrap, configure and deploy containers
    for the service.

  - ``reconfigure.yml`` : Used to push new configuration files to the host
    and restart the service.

  - ``pull.yml`` : Used to pre fetch the image into the Docker image cache
    on hosts, to speed up initial deploys.

  - ``upgrade.yml`` : Used for upgrading the service in a rolling fashion. May
    include service specific setup and steps as not all services can be
    upgraded in the same way.

* Log rotation

  - For OpenStack services there should be a ``cron-logrotate-PROJECT.conf.j2``
    template file in ``ansible/roles/cron/templates`` with the following
    content:

    .. path ansible/roles/cron/templates/cron-logrotate-PROJECT.conf.j2
    .. code-block:: console

       "/var/log/kolla/PROJECT/*.log"
       {
       }

  - For OpenStack services there should be an entry in the ``services`` list
    in the ``cron.json.j2`` template file in ``ansible/roles/cron/templates``.

* Log delivery

  - For OpenStack services the service should add a new ``rewriterule`` in the
    ``match`` element in the ``01-rewrite.conf.j2`` template file in
    ``ansible/roles/fluentd/templates/conf/filter`` to deliver log messages to
    Opensearch.

* Documentation

  - For OpenStack services there should be an entry in the list
    ``OpenStack services`` in the ``README.rst`` file.

  - For infrastructure services there should be an entry in the list
    ``Infrastructure components`` in the ``README.rst`` file.

* Syntax

  - All YAML data files should start with three dashes (``---``).

Other than the above, most service roles abide by the following pattern:

* ``Register``: Involves registering the service with Keystone, creating
  endpoints, roles, users, etc.

* ``Config``: Distributes the config files to the nodes to be pulled into
  the container on startup.

* ``Bootstrap``: Creating the database (but not tables), database user for
  the service, permissions, etc.

* ``Bootstrap Service``: Starts a one shot container on the host to create
  the database tables, and other initial run time config.

Ansible handlers are used to create or restart containers when necessary.
