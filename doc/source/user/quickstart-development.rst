.. quickstart-development:

===========================
Quick Start for development
===========================

This guide provides step by step instructions to deploy OpenStack using Kolla
Ansible on bare metal servers or virtual machines. For deployment/evaluation we
have the :kolla-ansible-doc:`quickstart <user/quickstart>` guide.

Recommended reading
~~~~~~~~~~~~~~~~~~~

It's beneficial to learn basics of both `Ansible <https://docs.ansible.com>`__
and `Docker <https://docs.docker.com>`__ before running Kolla Ansible.

Host machine requirements
~~~~~~~~~~~~~~~~~~~~~~~~~

The host machine must satisfy the following minimum requirements:

* 2 network interfaces
* 8GB main memory
* 40GB disk space

See the :kolla-ansible-doc:`support matrix <user/support-matrix>` for details
of supported host Operating Systems. Kolla Ansible supports the default Python
3.x versions provided by the supported Operating Systems. For more information
see `tested runtimes <|TESTED_RUNTIMES_GOVERNANCE_URL|>`_.

Install dependencies
~~~~~~~~~~~~~~~~~~~~

Typically commands that use the system package manager in this section must be
run with root privileges.

It is generally recommended to use a virtual environment to install Kolla
Ansible and its dependencies, to avoid conflicts with the system site packages.
Note that this is independent from the use of a virtual environment for remote
execution, which is described in
:kolla-ansible-doc:`Virtual Environments <user/virtual-environments.html>`.

#. For Debian or Ubuntu, update the package index.

   .. code-block:: console

      sudo apt update

#. Install Python build dependencies:

   For CentOS or Rocky, run:

   .. code-block:: console

      sudo dnf install git python3-devel libffi-devel gcc openssl-devel python3-libselinux

   For Debian or Ubuntu, run:

   .. code-block:: console

      sudo apt install git python3-dev libffi-dev gcc libssl-dev libdbus-glib-1-dev

Install dependencies for the virtual environment
------------------------------------------------

#. Install the virtual environment dependencies.

   For CentOS or Rocky, you don't need to do anything.

   For Debian or Ubuntu, run:

   .. code-block:: console

      sudo apt install python3-venv

#. Create a virtual environment and activate it:

   .. code-block:: console

      python3 -m venv /path/to/venv
      source /path/to/venv/bin/activate

   The virtual environment should be activated before running any commands that
   depend on packages installed in it.

#. Ensure the latest version of pip is installed:

   .. code-block:: console

      pip install -U pip

Install Kolla-ansible
~~~~~~~~~~~~~~~~~~~~~

#. Clone ``kolla-ansible`` repository from git.

   .. code-block:: console

      git clone --branch |KOLLA_BRANCH_NAME| https://opendev.org/openstack/kolla-ansible

#. Install requirements of ``kolla`` and ``kolla-ansible``:

   .. code-block:: console

      pip install -e ./kolla-ansible

#. Create the ``/etc/kolla`` directory.

   .. code-block:: console

      sudo mkdir -p /etc/kolla
      sudo chown $USER:$USER /etc/kolla

#. Copy the configuration files to ``/etc/kolla`` directory.
   ``kolla-ansible`` holds the configuration files (``globals.yml`` and
   ``passwords.yml``) in ``etc/kolla``.

   .. code-block:: console

      cp -r kolla-ansible/etc/kolla/* /etc/kolla

#. Copy the inventory files to the current directory. ``kolla-ansible`` holds
   inventory files (``all-in-one`` and ``multinode``) in the
   ``ansible/inventory`` directory.

   .. code-block:: console

      cp kolla-ansible/ansible/inventory/* .

Install Ansible Galaxy requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install Ansible Galaxy dependencies:

.. code-block:: console

   kolla-ansible install-deps

Prepare initial configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inventory
---------

The next step is to prepare our inventory file. An inventory is an Ansible file
where we specify hosts and the groups that they belong to. We can use this to
define node roles and access credentials.

Kolla Ansible comes with ``all-in-one`` and ``multinode`` example inventory
files. The difference between them is that the former is ready for deploying
single node OpenStack on localhost. In this Guide we will show the
``all-in-one`` Installation.

Kolla passwords
---------------

Passwords used in our deployment are stored in ``/etc/kolla/passwords.yml``
file. All passwords are blank in this file and have to be filled either
manually or by running random password generator:

.. code-block:: console

   cd kolla-ansible/tools
   ./generate_passwords.py

Kolla globals.yml
-----------------

``globals.yml`` is the main configuration file for Kolla Ansible and per
default stored in /etc/kolla/globals.yml.
There are a few options that are required to deploy Kolla Ansible:

* Image options

  User has to specify images that are going to be used for our deployment.
  In this guide
  `Quay.io <https://quay.io/organization/openstack.kolla>`__-provided,
  pre-built images are going to be used. To learn more about building
  mechanism, please refer :kolla-doc:`Building Container Images
  <admin/image-building.html>`.

  Kolla provides choice of several Linux distributions in containers:

  - CentOS Stream (``centos``)
  - Debian (``debian``)
  - Rocky (``rocky``)
  - Ubuntu (``ubuntu``)

  For newcomers, we recommend to use Rocky Linux 10 or Ubuntu 24.04.

  .. code-block:: console

     kolla_base_distro: "rocky"

* AArch64 options

  Kolla provides images for both x86-64 and aarch64 architectures. They are not
  "multiarch" so users of aarch64 need to define "openstack_tag_suffix"
  setting:

  .. code-block:: console

     openstack_tag_suffix: "-aarch64"

  This way images built for aarch64 architecture will be used.


* Networking

  Kolla Ansible requires a few networking options to be set.
  We need to set network interfaces used by OpenStack.

  First interface to set is "network_interface". This is the default interface
  for multiple management-type networks.

  .. code-block:: console

     network_interface: "eth0"

  Second interface required is dedicated for Neutron external (or public)
  networks, can be vlan or flat, depends on how the networks are created.
  This interface should be active without IP address. If not, instances
  won't be able to access to the external networks.

  .. code-block:: console

     neutron_external_interface: "eth1"

  To learn more about network configuration, refer
  :kolla-ansible-doc:`Network overview
  <admin/production-architecture-guide.html#network-configuration>`.

  Next we need to provide floating IP for management traffic. This IP will be
  managed by keepalived to provide high availability, and should be set to be
  *not used* address in management network that is connected to our
  ``network_interface``. If you use an existing OpenStack installation for your
  deployment, make sure the IP is allowed in the configuration of your VM.

  .. code-block:: console

     kolla_internal_vip_address: "10.1.0.250"

* Enable additional services

  By default Kolla Ansible provides a bare compute kit, however it does provide
  support for a vast selection of additional services. To enable them, set
  ``enable_*`` to "yes".

  Kolla now supports many OpenStack services, there is
  `a list of available services
  <https://opendev.org/openstack/kolla-ansible/src/branch/master/README.rst#openstack-services>`_.
  For more information about service configuration, Please refer to the
  :kolla-ansible-doc:`Services Reference Guide
  <reference/index.html>`.

* Multiple globals files

  For a more granular control, enabling any option from the main
  ``globals.yml`` file can now be done using multiple yml files. Simply,
  create a directory called ``globals.d`` under ``/etc/kolla/`` and place
  all the relevant ``*.yml`` files in there. The ``kolla-ansible`` script
  will, automatically, add all of them as arguments to the ``ansible-playbook``
  command.

  An example use case for this would be if an operator wants to enable cinder
  and all its options, at a later stage than the initial deployment, without
  tampering with the existing ``globals.yml`` file. That can be achieved, using
  a separate ``cinder.yml`` file, placed under the ``/etc/kolla/globals.d/``
  directory and adding all the relevant options in there.

* Virtual environment

  It is recommended to use a virtual environment to execute tasks on the remote
  hosts. This is covered in
  :kolla-ansible-doc:`Virtual Environments <user/virtual-environments.html>`.

Deployment
~~~~~~~~~~

After configuration is set, we can proceed to the deployment phase. First we
need to setup basic host-level dependencies, like docker.

Kolla Ansible provides a playbook that will install all required services in
the correct versions.

The following assumes the use of the ``all-in-one`` inventory. If using a
different inventory, such as ``multinode``, replace the ``-i`` argument
accordingly.

#. Bootstrap servers with kolla deploy dependencies:

  .. code-block:: console

     kolla-ansible bootstrap-servers -i ../all-in-one

#. Do pre-deployment checks for hosts:

  .. code-block:: console

     kolla-ansible prechecks -i ../all-in-one

#. Finally proceed to actual OpenStack deployment:

  .. code-block:: console

     kolla-ansible deploy -i ../all-in-one

When this playbook finishes, OpenStack should be up, running and functional!
If error occurs during execution, refer to
:kolla-ansible-doc:`troubleshooting guide <user/troubleshooting.html>`.

Using OpenStack
~~~~~~~~~~~~~~~

#. Install the OpenStack CLI client:

   .. code-block:: console

      pip install python-openstackclient -c https://releases.openstack.org/constraints/upper/|KOLLA_OPENSTACK_RELEASE|

#. OpenStack requires a ``clouds.yaml`` file where credentials for the
   admin user are set. To generate this file:

     .. code-block:: console

        kolla-ansible post-deploy

   * The file will be generated in /etc/kolla/clouds.yaml, you can use it by
     copying it to /etc/openstack or ~/.config/openstack or setting
     OS_CLIENT_CONFIG_FILE environment variable.

#. Depending on how you installed Kolla Ansible, there is a script that will
   create example networks, images, and so on.

   .. warning::

      You are free to use the following ``init-runonce`` script for demo
      purposes but note it does **not** have to be run in order to use your
      cloud. Depending on your customisations, it may not work, or it may
      conflict with the resources you want to create. You have been warned.

  .. code-block:: console

     kolla-ansible/tools/init-runonce
