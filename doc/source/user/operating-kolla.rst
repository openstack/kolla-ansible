.. _operating-kolla:

===============
Operating Kolla
===============

Tools versioning
~~~~~~~~~~~~~~~~

Kolla and Kolla Ansible use the ``x.y.z`` `semver <https://semver.org/>`_
nomenclature for naming versions, with major version increasing with each
new series, e.g., Wallaby.
The tools are designed to, respectively, build and deploy Docker images of
OpenStack services of that series.
Users are advised to run the latest version of tools for the series they
target, preferably by installing directly from the relevant branch of the Git
repository, e.g.:

.. code-block:: console

   pip3 install --upgrade git+https://opendev.org/openstack/kolla-ansible@|KOLLA_BRANCH_NAME|

Version of deployed images
~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, Kolla Ansible will deploy or upgrade using the series name embedded
in the internal config (``openstack_release``) and it is not recommended to
tweak this unless using a local registry and a custom versioning policy, e.g.,
when users want to control when services are upgraded and to which version,
possibly on a per-service basis (but this is an advanced use case scenario).

Upgrade procedure
~~~~~~~~~~~~~~~~~

.. note::

   This procedure is for upgrading from series to series, not for doing updates
   within a series.
   Inside a series, it is usually sufficient to just update the
   ``kolla-ansible`` package, rebuild (if needed) and pull the images,
   and run ``kolla-ansible deploy`` again.
   Please follow release notes to check if there are any issues to be aware of.

.. note::

   If you have set ``enable_cells`` to ``yes`` then you should read the
   upgrade notes in the :ref:`Nova cells guide<nova-cells-upgrade>`.

Kolla's strategy for upgrades is to never make a mess and to follow consistent
patterns during deployment such that upgrades from one environment to the next
are simple to automate.

Kolla Ansible implements a single command operation for upgrading an existing
deployment.

Limitations and Recommendations
-------------------------------

.. note::

   Please note that when the ``use_preconfigured_databases`` flag is set to
   ``"yes"``, you need to have the ``log_bin_trust_function_creators`` set to
   ``1`` by your database administrator before performing the upgrade.

.. note::

   If you have separate keys for nova and cinder, please be sure to set
   ``ceph_nova_keyring: ceph.client.nova.keyring`` and ``ceph_nova_user: nova``
   in ``/etc/kolla/globals.yml``

Ubuntu Focal 20.04
------------------

The Victoria release adds support for Ubuntu Focal 20.04 as a host operating
system. Ubuntu users upgrading from Ussuri should first upgrade OpenStack
containers to Victoria, which uses the Ubuntu Focal 20.04 base container image.
Hosts should then be upgraded to Ubuntu Focal 20.04.

CentOS Stream 8
---------------

The Wallaby release adds support for CentOS Stream 8 as a host operating
system. CentOS Stream 8 support will also be added to a Victoria stable
release. CentOS Linux users upgrading from Victoria should first migrate hosts
and container images from CentOS Linux to CentOS Stream before upgrading to
Wallaby.

Preparation (the foreword)
--------------------------

Before preparing the upgrade plan and making any decisions, please read the
`release notes <https://docs.openstack.org/releasenotes/kolla-ansible/index.html>`__
for the series you are targeting, especially the `Upgrade notes` that we
publish for your convenience and awareness.

Before you begin, **make a backup of your config**. On the operator/deployment
node, copy the contents of the config directory (``/etc/kolla`` by default) to
a backup place (or use versioning tools, like git, to keep previous versions
of config in a safe place).

Preparation (the real deal)
---------------------------

First, upgrade the ``kolla-ansible`` package:

.. code-block:: console

   pip3 install --upgrade git+https://opendev.org/openstack/kolla-ansible@|KOLLA_BRANCH_NAME|

.. note::

   If you are running from Git repository, then just checkout the desired
   branch and run ``pip3 install --upgrade`` with the repository directory.

If upgrading to a Yoga release or later, install or upgrade Ansible Galaxy
dependencies:

.. code-block:: console

   kolla-ansible install-deps

The inventory file for the deployment should be updated, as the newer sample
inventory files may have updated layout or other relevant changes.
The ``diff`` tool (or similar) is your friend in this task.
If using a virtual environment, the sample inventories are in
``/path/to/venv/share/kolla-ansible/ansible/inventory/``, else they are
most likely in
``/usr/local/share/kolla-ansible/ansible/inventory/``.

Other files which may need manual updating are:

- ``/etc/kolla/globals.yml``
- ``/etc/kolla/passwords.yml``

For ``globals.yml``, it is best to follow the release notes (mentioned above).
For ``passwords.yml``, one needs to use ``kolla-mergepwd`` and ``kolla-genpwd``
tools.

``kolla-mergepwd --old OLD_PASSWDS --new NEW_PASSWDS --final FINAL_PASSWDS``
is used to merge passwords from old installation with newly generated
passwords. The workflow is:

#. Save old passwords from ``/etc/kolla/passwords.yml`` into
   ``passwords.yml.old``.
#. Generate new passwords via ``kolla-genpwd`` as ``passwords.yml.new``.
#. Merge ``passwords.yml.old`` and ``passwords.yml.new`` into
   ``/etc/kolla/passwords.yml``.

For example:

.. code-block:: console

   cp /etc/kolla/passwords.yml passwords.yml.old
   cp kolla-ansible/etc/kolla/passwords.yml passwords.yml.new
   kolla-genpwd -p passwords.yml.new
   kolla-mergepwd --old passwords.yml.old --new passwords.yml.new --final /etc/kolla/passwords.yml

.. note::

   ``kolla-mergepwd``, by default, keeps old, unused passwords intact.
   To alter this behavior, and remove such entries, use the ``--clean``
   argument when invoking ``kolla-mergepwd``.

Run the command below to pull the new images on target hosts:

.. code-block:: console

   kolla-ansible pull

It is also recommended to run prechecks to identify potential configuration
issues:

.. code-block:: console

   kolla-ansible prechecks

At a convenient time, the upgrade can now be run.

Perform the Upgrade
-------------------

To perform the upgrade:

.. code-block:: console

   kolla-ansible upgrade

After this command is complete, the containers will have been recreated from
the new images and all database schema upgrades and similar actions performed
for you.

Cleanup the Keystone admin port (Zed only)
------------------------------------------

The Keystone admin port is no longer used in Zed. The admin interface points
to the common port. However, during upgrade, the port is preserved for
intermediate compatibility. To clean up the port, it is necessary to run
the ``deploy`` action for Keystone. Additionally, the generated
``admin-openrc.sh`` file may need regeneration as it used the admin
port:

.. code-block:: console

   kolla-ansible deploy --tags keystone
   kolla-ansible post-deploy

After these commands are complete, there are no leftovers of the admin port.

Tips and Tricks
~~~~~~~~~~~~~~~

Kolla Ansible CLI
-----------------

When running the ``kolla-ansible`` CLI, additional arguments may be passed to
``ansible-playbook`` via the ``EXTRA_OPTS`` environment variable.

``kolla-ansible -i INVENTORY deploy`` is used to deploy and start all Kolla
containers.

``kolla-ansible -i INVENTORY destroy`` is used to clean up containers and
volumes in the cluster.

``kolla-ansible -i INVENTORY mariadb_recovery`` is used to recover a
completely stopped mariadb cluster.

``kolla-ansible -i INVENTORY prechecks`` is used to check if all requirements
are meet before deploy for each of the OpenStack services.

``kolla-ansible -i INVENTORY post-deploy`` is used to do post deploy on deploy
node to get the admin openrc file.

``kolla-ansible -i INVENTORY pull`` is used to pull all images for containers.

``kolla-ansible -i INVENTORY reconfigure`` is used to reconfigure OpenStack
service.

``kolla-ansible -i INVENTORY upgrade`` is used to upgrades existing OpenStack
Environment.

``kolla-ansible -i INVENTORY stop`` is used to stop running containers.

``kolla-ansible -i INVENTORY deploy-containers`` is used to check and if
necessary update containers, without generating configuration.

``kolla-ansible -i INVENTORY prune-images`` is used to prune orphaned Docker
images on hosts.

``kolla-ansible -i INVENTORY1 -i INVENTORY2 ...`` Multiple inventories can be
specified by passing the ``--inventory`` or ``-i`` command line option multiple
times. This can be useful to share configuration between multiple environments.
Any common configuration can be set in ``INVENTORY1`` and ``INVENTORY2`` can be
used to set environment specific details.

``kolla-ansible -i INVENTORY gather-facts`` is used to gather Ansible facts,
for example to populate a fact cache.

Using Hashicorp Vault for password storage
------------------------------------------

Hashicorp Vault can be used as an alternative to Ansible Vault for storing
passwords generated by Kolla Ansible. To use Hashicorp Vault as the secrets
store you will first need to generate the passwords, and then you can
save them into an existing KV using the following command:

.. code-block:: console

   kolla-writepwd \
   --passwords /etc/kolla/passwords.yml \
   --vault-addr <VAULT_ADDRESS> \
   --vault-token <VAULT_TOKEN>

.. note::

   For a full list of ``kolla-writepwd`` arguments, use the ``--help``
   argument when invoking ``kolla-writepwd``.

To read passwords from Hashicorp Vault and generate a passwords.yml:

.. code-block:: console

   mv kolla-ansible/etc/kolla/passwords.yml /etc/kolla/passwords.yml
   kolla-readpwd \
   --passwords /etc/kolla/passwords.yml \
   --vault-addr <VAULT_ADDRESS> \
   --vault-token <VAULT_TOKEN>

Tools
-----

Kolla ships with several utilities intended to facilitate ease of operation.

``tools/cleanup-containers`` is used to remove deployed containers from the
system. This can be useful when you want to do a new clean deployment. It will
preserve the registry and the locally built images in the registry, but will
remove all running Kolla containers from the local Docker daemon. It also
removes the named volumes.

``tools/cleanup-host`` is used to remove remnants of network changes
triggered on the Docker host when the neutron-agents containers are launched.
This can be useful when you want to do a new clean deployment, particularly one
changing the network topology.

``tools/cleanup-images --all`` is used to remove all Docker images built by
Kolla from the local Docker cache.
