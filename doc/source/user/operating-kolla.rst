.. _operating-kolla:

===============
Operating Kolla
===============

Versioning
~~~~~~~~~~

Kolla uses the ``x.y.z`` `semver <https://semver.org/>`_ nomenclature for
naming versions. Kolla's initial Pike release was ``5.0.0`` and the initial
Queens release is ``6.0.0``. The Kolla community commits to release z-stream
updates every 45 days that resolve defects in the stable version in use and
publish those images to the Docker Hub registry.

To prevent confusion, the Kolla community recommends using an alpha identifier
``x.y.z.a`` where ``a`` represents any customization done on the part of the
operator. For example, if an operator intends to modify one of the Docker files
or the repos from the originals and build custom images for the Pike version,
the operator should start with version 5.0.0.0 and increase alpha for each
release. Alpha tag usage is at discretion of the operator. The alpha identifier
could be a number as recommended or a string of the operator's choosing.

To customize the version number uncomment ``openstack_release`` in globals.yml
and specify the version number desired. If ``openstack_release`` is not
specified, Kolla will deploy or upgrade using the version number information
contained in the kolla-ansible package.

Upgrade procedure
~~~~~~~~~~~~~~~~~

Kolla's strategy for upgrades is to never make a mess and to follow consistent
patterns during deployment such that upgrades from one environment to the next
are simple to automate.

Kolla implements a one command operation for upgrading an existing deployment
consisting of a set of containers and configuration data to a new deployment.

Limitations and Recommendations
-------------------------------

.. note::

   Varying degrees of success have been reported with upgrading the libvirt
   container with a running virtual machine in it. The libvirt upgrade still
   needs a bit more validation, but the Kolla community feels confident this
   mechanism can be used with the correct Docker graph driver.

.. note::

   The Kolla community recommends the btrfs or aufs graph drivers for storing
   data as sometimes the LVM graph driver loses track of its reference counting
   and results in an unremovable container.

.. note::

   Because of system technical limitations, upgrade of a libvirt container when
   using software emulation (``virt_type = qemu`` in nova.conf), does not work
   at all. This is acceptable because KVM is the recommended virtualization
   driver to use with Nova.

.. note::

   Please note that when the ``use_preconfigured_databases`` flag is set to
   ``"yes"``, you need to have the ``log_bin_trust_function_creators`` set to
   ``1`` by your database administrator before performing the upgrade.

Preparation
-----------

While there may be some cases where it is possible to upgrade by skipping this
step (i.e. by upgrading only the ``openstack_release`` version) - generally,
when looking at a more comprehensive upgrade, the kolla-ansible package itself
should be upgraded first. This will include reviewing some of the configuration
and inventory files. On the operator/master node, a backup of the
``/etc/kolla`` directory may be desirable.

If upgrading from ``5.0.0`` to ``6.0.0``, upgrade the kolla-ansible package:

.. code-block:: console

   pip install --upgrade kolla-ansible==6.0.0

If this is a minor upgrade, and you do not wish to upgrade kolla-ansible
itself, you may skip this step.

The inventory file for the deployment should be updated, as the newer sample
inventory files may have updated layout or other relevant changes.
Use the newer ``6.0.0`` one as a starting template, and merge your existing
inventory layout into a copy of the one from here::

    /usr/share/kolla-ansible/ansible/inventory/

In addition the ``6.0.0`` sample configuration files should be taken from::

    # CentOS
    /usr/share/kolla-ansible/etc_examples/kolla

    # Ubuntu
    /usr/local/share/kolla-ansible/etc_examples/kolla

At this stage, files that are still at the ``5.0.0`` version - which need
manual updating are:

- ``/etc/kolla/globals.yml``
- ``/etc/kolla/passwords.yml``

For ``globals.yml`` relevant changes should be merged into a copy of the new
template, and then replace the file in ``/etc/kolla`` with the updated version.
For ``passwords.yml``, see the ``kolla-mergepwd`` instructions in
`Tips and Tricks`.

For the kolla docker images, the ``openstack_release`` is updated to ``6.0.0``:

.. code-block:: yaml

   openstack_release: 6.0.0

Once the kolla release, the inventory file, and the relevant configuration
files have been updated in this way, the operator may first want to 'pull'
down the images to stage the ``6.0.0`` versions. This can be done safely
ahead of time, and does not impact the existing services. (optional)

Run the command to pull the ``6.0.0`` images for staging:

.. code-block:: console

   kolla-ansible pull

At a convenient time, the upgrade can now be run (it will complete more
quickly if the images have been staged ahead of time).

Perform the Upgrade
-------------------

To perform the upgrade:

.. code-block:: console

   kolla-ansible upgrade

After this command is complete the containers will have been recreated from the
new images.

Tips and Tricks
~~~~~~~~~~~~~~~

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

``kolla-ansible -i INVENTORY check`` is used to do post-deployment smoke
tests.

``kolla-ansible -i INVENTORY stop`` is used to stop running containers.

.. note::

   In order to do smoke tests, requires ``kolla_enable_sanity_checks=yes``.

``kolla-mergepwd --old OLD_PASSWDS --new NEW_PASSWDS --final FINAL_PASSWDS``
is used to merge passwords from old installation with newly generated
passwords during upgrade of Kolla release. The workflow is:

#. Save old passwords from ``/etc/kolla/passwords.yml`` into
   ``passwords.yml.old``.
#. Generate new passwords via ``kolla-genpwd`` as ``passwords.yml.new``.
#. Merge ``passwords.yml.old`` and ``passwords.yml.new`` into
   ``/etc/kolla/passwords.yml``.

For example:

.. code-block:: console

   mv /etc/kolla/passwords.yml passwords.yml.old
   cp kolla-ansible/etc/kolla/passwords.yml passwords.yml.new
   kolla-genpwd -p passwords.yml.new
   kolla-mergepwd --old passwords.yml.old --new passwords.yml.new --final /etc/kolla/passwords.yml

