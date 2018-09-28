.. _CONTRIBUTING:

=================
How To Contribute
=================

Basics
======

#. Our source code is hosted on `OpenStack Kolla-Ansible Git
   <https://git.openstack.org/cgit/openstack/kolla-ansible/>`_. Bugs should be
   filed on `launchpad <https://bugs.launchpad.net/kolla-ansible>`_.

#. Please follow OpenStack `Gerrit Workflow
   <https://docs.openstack.org/infra/manual/developers.html#development-workflow>`__
   to contribute to Kolla-ansible.

#. Note the branch you're proposing changes to. ``master`` is the current focus
   of development. Kolla project has a strict policy of only allowing backports
   in ``stable/branch``, unless when not applicable. A bug in a
   ``stable/branch`` will first have to be fixed in ``master``.

#. Please file a `blueprint of kolla-ansible <https://blueprints.launchpad.net/kolla-ansible>`__
   for any significant code change and a bug for any significant bug fix,
   or add a ``TrivialFix`` tag to commit message for simple changes.
   See how to reference a bug or a blueprint in the `commit message
   <https://wiki.openstack.org/wiki/GitCommitMessages>`_.

#. TrivialFix tags or bugs are not required for documentation changes.

Development Environment
=======================

Please follow our :doc:`/user/quickstart` to deploy your environment and test
your changes.

Please use the existing sandbox repository, available at `sandbox
<https://git.openstack.org/cgit/openstack-dev/sandbox>`_, for learning, understanding
and testing the `Gerrit Workflow
<https://docs.openstack.org/infra/manual/developers.html#development-workflow>`_.

Adding a new service
====================

Kolla aims to both containerise and deploy all services within the OpenStack
"big tent". This is a constantly moving target as the ecosystem grows, so these
guidelines aim to help make adding a new service to Kolla a smooth experience.

When adding a role for a new service in Ansible, there are couple of patterns
that Kolla uses throughout that should be followed.

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

  - ``reconfigure.yml`` : Used to push new configuration files to the host
    and restart the service.

  - ``pull.yml`` : Used to pre fetch the image into the Docker image cache
    on hosts, to speed up initial deploys.

  - ``upgrade.yml`` : Used for upgrading the service in a rolling fashion. May
    include service specific setup and steps as not all services can be
    upgraded in the same way.

* Logrotation

  - For OpenStack services there should be a ``cron-logrotate-PROJECT.conf.j2``
    template file in ``ansible/roles/common/templates`` with the following
    content:

    .. path ansible/roles/common/templates/cron-logrotate-PROJECT.conf.j2
    .. code-block:: console

       "/var/log/kolla/PROJECT/*.log"
       {
       }

  - For OpenStack services there should be an entry in the ``services`` list
    in the ``cron.json.j2`` template file in ``ansible/roles/common/templates``.

* Log delivery

  - For OpenStack services the service should add a new ``rewriterule`` in the
    ``match`` element in the ``01-rewrite.conf.j2`` template file in
    ``ansible/roles/common/templates/conf/filter`` to deliver log messages to
    Elasticsearch.

* Documentation

  - For OpenStack services there should be an entry in the list
    ``OpenStack services`` in the ``README.rst`` file.

  - For infrastructure services there should be an entry in the list
    ``Infrastructure components`` in the ``README.rst`` file.

* Syntax

  - All YAML data files should start with three dashes (``---``).

Other than the above, most service roles abide by the following pattern:

- ``Register``: Involves registering the service with Keystone, creating
  endpoints, roles, users, etc.

- ``Config``: Distributes the config files to the nodes to be pulled into
  the container on startup.

- ``Bootstrap``: Creating the database (but not tables), database user for
  the service, permissions, etc.

- ``Bootstrap Service``: Starts a one shot container on the host to create
  the database tables, and other initial run time config.

- ``Start``: Start the service(s).
