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

.. warning::

   Please notice that using the ansible ``--limit`` option is not recommended.
   The reason is, that there are known bugs with it, e.g. when `upgrading parts of nova.
   <https://bugs.launchpad.net/kolla-ansible/+bug/2054348>`__
   We accept bug reports for this and try to fix issues when they are known.
   The core problem is how the ``register:`` keyword works and how it
   interacts with the ``--limit`` option. You can find more information in the above
   bug report.

.. note::

   Please note that when the ``use_preconfigured_databases`` flag is set to
   ``"yes"``, you need to have the ``log_bin_trust_function_creators`` set to
   ``1`` by your database administrator before performing the upgrade.

.. note::

   If you have separate keys for nova and cinder, please be sure to set
   ``ceph_nova_user: nova`` in ``/etc/kolla/globals.yml``

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

If performing a skip-level (SLURP) upgrade, update ``ansible`` or
``ansible-core`` to a version supported by the release you're upgrading to.

.. code-block:: console

   pip3 install --upgrade 'ansible-core>=|ANSIBLE_CORE_VERSION_MIN|,<|ANSIBLE_CORE_VERSION_MAX|.99'

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

* ``/etc/kolla/globals.yml``
* ``/etc/kolla/passwords.yml``

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

SLURP extra preparations
++++++++++++++++++++++++

RabbitMQ has two major version releases per year but does not support jumping
two versions in one upgrade. So if you want to perform a skip-level upgrade,
you must first upgrade RabbitMQ to an intermediary version. Please see the
`RabbitMQ SLURP section
<https://docs.openstack.org/kolla-ansible/latest/reference/message-queues/rabbitmq.html#slurp>`__
for details.

Perform the Upgrade
-------------------

To perform the upgrade:

.. code-block:: console

   kolla-ansible upgrade

After this command is complete, the containers will have been recreated from
the new images and all database schema upgrades and similar actions performed
for you.


CLI Command Completion
~~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible supports shell command completion to make the CLI easier to use.

To enable Bash completion, generate the completion script:

.. code-block:: console

   kolla-ansible complete --shell bash > ~/.kolla_ansible_completion.sh

Then, add the following line to your ``~/.bashrc`` file:

.. code-block:: console

   source ~/.kolla_ansible_completion.sh

Finally, reload your shell configuration:

.. code-block:: console

   source ~/.bashrc

.. note::

   If you're using a shell other than Bash, replace ``--shell bash`` with your shell type,
   e.g., ``zsh``, and adapt your shell's configuration file accordingly.


Tips and Tricks
~~~~~~~~~~~~~~~

Kolla Ansible CLI
-----------------

``kolla-ansible deploy -i INVENTORY`` is used to deploy and start all Kolla
containers.

``kolla-ansible destroy -i INVENTORY`` is used to clean up containers and
volumes in the cluster.

``kolla-ansible mariadb_recovery -i INVENTORY`` is used to recover a
completely stopped mariadb cluster.

``kolla-ansible prechecks -i INVENTORY`` is used to check if all requirements
are met before deployment for each of the OpenStack services.

``kolla-ansible post-deploy -i INVENTORY`` is used to do post deploy on deploy
node to get the admin openrc file.

``kolla-ansible pull -i INVENTORY`` is used to pull all images for containers.

``kolla-ansible reconfigure -i INVENTORY`` is used to reconfigure OpenStack
service.

``kolla-ansible upgrade -i INVENTORY`` is used to upgrades existing OpenStack
Environment.

``kolla-ansible stop -i INVENTORY`` is used to stop running containers.

``kolla-ansible deploy-containers -i INVENTORY`` is used to check and if
necessary update containers, without generating configuration.

``kolla-ansible prune-images -i INVENTORY`` is used to prune orphaned Docker
images on hosts.

``kolla-ansible genconfig -i INVENTORY`` is used to generate configuration
files for enabled OpenStack services, without then restarting the containers so
it is not applied right away.

``kolla-ansible validate-config -i INVENTORY`` is used to validate generated
configuration files of enabled OpenStack services. By default, the results are
saved to ``/var/log/kolla/config-validate`` when issues are detected.

``kolla-ansible ... -i INVENTORY1 -i INVENTORY2`` Multiple inventories can be
specified by passing the ``--inventory`` or ``-i`` command line option multiple
times. This can be useful to share configuration between multiple environments.
Any common configuration can be set in ``INVENTORY1`` and ``INVENTORY2`` can be
used to set environment specific details.

``kolla-ansible gather-facts -i INVENTORY`` is used to gather Ansible facts,
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
