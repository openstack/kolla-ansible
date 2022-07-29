=====================
Bootstrapping Servers
=====================

Kolla-ansible provides support for bootstrapping host configuration prior to
deploying containers via the ``bootstrap-servers`` subcommand. This includes
support for the following:

* Customisation of ``/etc/hosts``
* Creation of user and group
* Kolla configuration directory
* Package installation and removal
* Docker engine installation and configuration
* Disabling firewalls
* Creation of Python virtual environment
* Configuration of Apparmor
* Configuration of SELinux
* Configuration of NTP daemon

All bootstrapping support is provided by the ``baremetal`` Ansible role.

Running the command
~~~~~~~~~~~~~~~~~~~

The base command to perform a bootstrap is:

.. code-block:: console

   kolla-ansible bootstrap-servers -i INVENTORY

Further options may be necessary, as described in the following sections.

Initial bootstrap considerations
--------------------------------

The nature of bootstrapping means that the environment that Ansible executes in
during the initial bootstrap may look different to that seen after
bootstrapping is complete. For example:

* The ``kolla_user`` user account may not yet have been created. If this is
  normally used as the ``ansible_user`` when executing Kolla Ansible, a
  different user account must be used for bootstrapping.
* The Python virtual environment may not exist. If a virtualenv is normally
  used as the ``ansible_python_interpreter`` when executing Kolla Ansible, the
  system python interpreter must be used for bootstrapping.

Each of these variables may be passed via the ``-e`` argument to Kolla Ansible
to override the inventory defaults:

.. code-block:: console

   kolla-ansible bootstrap-servers -i INVENTORY -e ansible_user=<bootstrap user> -e ansible_python_interpreter=/usr/bin/python

.. _rebootstrapping:

Subsequent bootstrap considerations
-----------------------------------

It is possible to run the bootstrapping process against a cloud that has
already been bootstrapped, for example to apply configuration from a newer
release of Kolla Ansible. In this case, further considerations should be
made.

It is possible that the Docker engine package will be updated. This will cause
the Docker engine to restart, in addition to all running containers. There are
three main approaches to avoiding all control plane services restarting
simultaneously.

The first option is to use the ``--limit`` command line argument to apply the
command to hosts in batches, ensuring there is always a quorum for clustered
services (e.g. MariaDB):

.. code-block:: console

   kolla-ansible bootstrap-servers -i INVENTORY --limit controller0,compute[0-1]
   kolla-ansible bootstrap-servers -i INVENTORY --limit controller1,compute[2-3]
   kolla-ansible bootstrap-servers -i INVENTORY --limit controller2,compute[4-5]

The second option is to execute individual plays on hosts in batches:

.. code-block:: console

   kolla-ansible bootstrap-servers -i INVENTORY -e kolla_serial=30%

The last option is to use the Docker ``live-restore`` configuration option to
avoid restarting containers when the Docker engine is restarted.  There have
been issues reported with using this option however, so use it at your own
risk.

Ensure that any operation that causes the Docker engine to be updated has been
tested, particularly when moving from legacy Docker packages to Docker
Community Edition. See :ref:`bootstrap-servers-docker-package-repos` for
details.

Customisation of ``/etc/hosts``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is optional, and enabled by ``customize_etc_hosts``, which is ``true`` by
default.

* Ensures that ``localhost`` is in ``/etc/hosts``
* Adds an entry for the IP of the API interface of each host to ``/etc/hosts``.

Creation of user and group
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is optional, and enabled by ``create_kolla_user``, which is ``true`` by
default.

* Ensures that a group exists with the name defined by the variable
  ``kolla_group`` with default ``kolla``.
* Ensures that a user exists with the name defined by the variable
  ``kolla_user`` with default ``kolla``. The user's primary group is defined by
  ``kolla_group``. The user is added to the ``sudo`` group.
* An SSH public key is authorised for ``kolla_user``.  The key is defined by
  the ``public_key`` value of the ``kolla_ssh_key`` mapping variable, typically
  defined in ``passwords.yml``.
* If the ``create_kolla_user_sudoers`` variable is set, a sudoers profile
  will be configured for ``kolla_user``, which grants passwordless sudo.

Kolla configuration directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla ansible service configuration is written to hosts in a directory defined
by ``node_config_directory``, which by default is ``/etc/kolla/``. This
directory will be created. If ``create_kolla_user`` is set, the owner and group
of the directory will be set to ``kolla_user`` and ``kolla_group``
respectively.

Package installation and removal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lists of packages are defined for installation and removal. On Debian family
systems, these are defined by ``debian_pkg_install`` and
``ubuntu_pkg_removals`` respectively. On Red Hat family systems, these are
defined by ``redhat_pkg_install`` and ``redhat_pkg_removals`` respectively.

Docker engine installation and configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Docker engine is a key dependency of Kolla Ansible, and various configuration
options are provided.

.. _bootstrap-servers-docker-package-repos:

Package repositories
--------------------

If the ``enable_docker_repo`` flag is set, then a package repository for Docker
packages will be configured. Kolla Ansible uses the
'Community Edition' packages from https://download.docker.com.

Various other configuration options are available beginning
``docker_(apt|yum)_``. Typically these do not need to be changed.

Configuration
-------------

The ``docker_storage_driver`` variable is optional. If set, it defines the
`storage driver
<https://docs.docker.com/storage/storagedriver/select-storage-driver/>`__ to
use for Docker.

The ``docker_runtime_directory`` variable is optional. If set, it defines the
runtime (``data-root``) directory for Docker.

The ``docker_registry`` variable, which is not set by default, defines the
address of the Docker registry. If the variable is not set,
`Quay.io <https://quay.io/organization/openstack.kolla>`__ will be used.

The ``docker_registry_insecure`` variable, which defaults to ``false``,
defines whether to configure ``docker_registry`` as an insecure registry.
Insecure registries allow to use broken certificate chains and HTTP without
TLS but it's strongly discouraged in production unless in very specific
circumstances. For more discussion, see the official Docker documentation on
`insecure registries <https://docs.docker.com/registry/insecure/>`__.
Additionally, notice this will disable Docker registry authentication.

The ``docker_log_max_file`` variable, which defaults to ``5``, defines the
maximum number of log files to retain per container. The
``docker_log_max_size`` variable, which defaults to ``50m``, defines the
maximum size of each rotated log file per container.

The ``docker_http_proxy``, ``docker_https_proxy`` and ``docker_no_proxy``
variables can be used to configure Docker Engine to connect to the internet
using http/https proxies.

Additional options for the Docker engine can be passed in
``docker_custom_config`` variable. It will be stored in ``daemon.json`` config
file. Example:

.. code-block:: json

    {
        "experimental": false
    }


Enabling/Disabling firewalls
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible supports configuration of host firewalls.

Currently only Firewalld is supported.

On Debian family systems Firewalld will need to be installed beforehand.

On Red Hat family systems firewalld should be installed by default.

To enable configuration of the system firewall set ``disable_firewall``
to ``false`` and set ``enable_external_api_firewalld`` to ``true``.

For further information. See :doc:`../../user/security`

Creation of Python virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is optional, and enabled by setting ``virtualenv`` to a path to a Python
virtual environment to create.  By default, a virtual environment is not used.
If ``virtualenv_site_packages`` is set, (default is ``true``) the virtual
environment will inherit packages from the global site-packages directory. This
is typically required for modules such as yum and apt which are not available
on PyPI. See :ref:`virtual-environments-target-hosts` for further information.

Configuration of Apparmor
~~~~~~~~~~~~~~~~~~~~~~~~~

On Ubuntu systems, the ``libvirtd`` Apparmor profile will be removed.

Configuration of SELinux
~~~~~~~~~~~~~~~~~~~~~~~~

On Red Hat family systems, if ``change_selinux`` is set (default is ``true``),
then the SELinux state will be set to ``selinux_state`` (default
``permissive``). See :doc:`../../user/security` for further information.
