.. quickstart:

===========
Quick Start
===========

This guide provides step by step instructions to deploy OpenStack using Kolla
Ansible on bare metal servers or virtual machines.

Recommended reading
~~~~~~~~~~~~~~~~~~~

It's beneficial to learn basics of both `Ansible <https://docs.ansible.com>`__
and `Docker <https://docs.docker.com>`__ before running Kolla-Ansible.

Host machine requirements
~~~~~~~~~~~~~~~~~~~~~~~~~

The host machine must satisfy the following minimum requirements:

- 2 network interfaces
- 8GB main memory
- 40GB disk space

See the :kolla-ansible-doc:`support matrix <user/support-matrix>` for details
of supported host Operating Systems.

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

      sudo apt-get update

#. Install Python build dependencies:

   For CentOS or RHEL 8, run:

   .. code-block:: console

      sudo dnf install python3-devel libffi-devel gcc openssl-devel python3-libselinux

   For Debian or Ubuntu, run:

   .. code-block:: console

      sudo apt-get install python3-dev libffi-dev gcc libssl-dev

Install dependencies using a virtual environment
------------------------------------------------

If not installing Kolla Ansible in a virtual environment, skip this section.

#. Install the virtual environment dependencies.

   For CentOS or RHEL 8, you don't need to do anything.

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

#. Install `Ansible <http://www.ansible.com>`__. Kolla Ansible requires at least
   Ansible ``2.8`` and supports up to ``2.9``.

   .. code-block:: console

      pip install 'ansible<2.10'

Install dependencies not using a virtual environment
----------------------------------------------------

If installing Kolla Ansible in a virtual environment, skip this section.

#. Install ``pip``.

   For CentOS or RHEL, run:

   .. code-block:: console

      sudo dnf install python3-pip

   For Debian or Ubuntu, run:

   .. code-block:: console

      sudo apt-get install python3-pip

#. Ensure the latest version of pip is installed:

   .. code-block:: console

      sudo pip3 install -U pip

#. Install `Ansible <http://www.ansible.com>`__. Kolla Ansible requires at least
   Ansible ``2.8`` and supports up to ``2.9``.

   For CentOS or RHEL, run:

   .. code-block:: console

      sudo dnf install ansible

   For Debian or Ubuntu, run:

   .. code-block:: console

      sudo apt-get install ansible

   .. note::

      If the installed Ansible version does not meet the requirements, one can
      use pip: ``sudo pip install -U 'ansible<2.10'``.
      Beware system package upgrades might interfere with that so it
      is recommended to uninstall the system package first. One might be better
      off with the virtual environment method to avoid this pitfall.

Install Kolla-ansible
~~~~~~~~~~~~~~~~~~~~~

Install Kolla-ansible for deployment or evaluation
--------------------------------------------------

#. Install kolla-ansible and its dependencies using ``pip``.

   If using a virtual environment:

   .. code-block:: console

      pip install kolla-ansible

   If not using a virtual environment:

   .. code-block:: console

      sudo pip3 install kolla-ansible

#. Create the ``/etc/kolla`` directory.

   .. code-block:: console

      sudo mkdir -p /etc/kolla
      sudo chown $USER:$USER /etc/kolla

#. Copy ``globals.yml`` and ``passwords.yml`` to ``/etc/kolla`` directory.

   If using a virtual environment:

   .. code-block:: console

      cp -r /path/to/venv/share/kolla-ansible/etc_examples/kolla/* /etc/kolla

   If not using a virtual environment, run:

   .. code-block:: console

      cp -r /usr/local/share/kolla-ansible/etc_examples/kolla/* /etc/kolla

#. Copy ``all-in-one`` and ``multinode`` inventory files to
   the current directory.

   If using a virtual environment:

   .. code-block:: console

      cp /path/to/venv/share/kolla-ansible/ansible/inventory/* .

   If not using a virtual environment, run:

   .. code-block:: console

      cp /usr/local/share/kolla-ansible/ansible/inventory/* .

Install Kolla for development
-----------------------------

#. Clone ``kolla`` and ``kolla-ansible`` repositories from git.

   .. code-block:: console

      git clone https://github.com/openstack/kolla
      git clone https://github.com/openstack/kolla-ansible

#. Install requirements of ``kolla`` and ``kolla-ansible``:

   If using a virtual environment:

   .. code-block:: console

      pip install ./kolla
      pip install ./kolla-ansible

   If not using a virtual environment:

   .. code-block:: console

      sudo pip3 install ./kolla
      sudo pip3 install ./kolla-ansible

#. Create the ``/etc/kolla`` directory.

   .. code-block:: console

      sudo mkdir -p /etc/kolla
      sudo chown $USER:$USER /etc/kolla

#. Copy the configuration files to ``/etc/kolla`` directory.
   ``kolla-ansible`` holds the configuration files ( ``globals.yml`` and
   ``passwords.yml``) in ``etc/kolla``.

   .. code-block:: console

      cp -r kolla-ansible/etc/kolla/* /etc/kolla

#. Copy the inventory files to the current directory. ``kolla-ansible`` holds
   inventory files ( ``all-in-one`` and ``multinode``) in the
   ``ansible/inventory`` directory.

   .. code-block:: console

      cp kolla-ansible/ansible/inventory/* .

Configure Ansible
~~~~~~~~~~~~~~~~~

For best results, Ansible configuration should be tuned for your environment.
For example, add the following options to the Ansible configuration file
``/etc/ansible/ansible.cfg``:

.. path /etc/ansible/ansible.cfg
.. code-block:: ini

   [defaults]
   host_key_checking=False
   pipelining=True
   forks=100

Further information on tuning Ansible is available `here
<https://www.ansible.com/blog/ansible-performance-tuning>`__.

Prepare initial configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inventory
---------

The next step is to prepare our inventory file. An inventory is an Ansible file
where we specify hosts and the groups that they belong to. We can use this to
define node roles and access credentials.

Kolla-Ansible comes with ``all-in-one`` and ``multinode`` example inventory
files. The difference between them is that the former is ready for deploying
single node OpenStack on localhost. If you need to use separate host or more
than one node, edit ``multinode`` inventory:

#. Edit the first section of ``multinode`` with connection details of your
   environment, for example:

   .. code-block:: ini

      [control]
      10.0.0.[10:12] ansible_user=ubuntu ansible_password=foobar ansible_become=true
      # Ansible supports syntax like [10:12] - that means 10, 11 and 12.
      # Become clause means "use sudo".

      [network:children]
      control
      # when you specify group_name:children, it will use contents of group specified.

      [compute]
      10.0.0.[13:14] ansible_user=ubuntu ansible_password=foobar ansible_become=true

      [monitoring]
      10.0.0.10
      # This group is for monitoring node.
      # Fill it with one of the controllers' IP address or some others.

      [storage:children]
      compute

      [deployment]
      localhost       ansible_connection=local become=true
      # use localhost and sudo

   To learn more about inventory files, check
   `Ansible documentation <http://docs.ansible.com/ansible/latest/intro_inventory.html>`_.

#. Check whether the configuration of inventory is correct or not, run:

   .. code-block:: console

      ansible -i multinode all -m ping

   .. note::

      Distributions might not come with Python pre-installed. That will cause
      errors in the ``ping`` module. To quickly install Python with Ansible you
      can run: for Debian or Ubuntu:
      ``ansible -i multinode all -m raw -a "apt-get -y install python3"``,
      and for CentOS or RHEL:
      ``ansible -i multinode all -m raw -a "dnf -y install python3"``.

Kolla passwords
---------------

Passwords used in our deployment are stored in ``/etc/kolla/passwords.yml``
file. All passwords are blank in this file and have to be filled either
manually or by running random password generator:

For deployment or evaluation, run:

.. code-block:: console

   kolla-genpwd

For development, run:

.. code-block:: console

   cd kolla-ansible/tools
   ./generate_passwords.py

Kolla globals.yml
-----------------

``globals.yml`` is the main configuration file for Kolla-Ansible.
There are a few options that are required to deploy Kolla-Ansible:

* Image options

  User has to specify images that are going to be used for our deployment.
  In this guide `DockerHub <https://hub.docker.com/u/kolla/>`__ provided
  pre-built images are going to be used. To learn more about building
  mechanism, please refer :kolla-doc:`Building Container Images
  <admin/image-building.html>`.

  Kolla provides choice of several Linux distributions in containers:

  - CentOS
  - Ubuntu
  - Debian
  - RHEL

  For newcomers, we recommend to use CentOS 8 or Ubuntu 18.04.

  .. code-block:: console

     kolla_base_distro: "centos"

  Next "type" of installation needs to be configured.
  Choices are:

  binary
   using repositories like apt or dnf

  source
   using raw source archives, git repositories or local source directory

  .. note::

     This only affects OpenStack services. Infrastructure services are
     always "binary".

  .. note::

     Source builds are proven to be slightly more reliable than binary.

  .. code-block:: console

     kolla_install_type: "source"

* Networking

  Kolla-Ansible requires a few networking options to be set.
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
  ``network_interface``.

  .. code-block:: console

     kolla_internal_vip_address: "10.1.0.250"

* Enable additional services

  By default Kolla-Ansible provides a bare compute kit, however it does provide
  support for a vast selection of additional services. To enable them, set
  ``enable_*`` to "yes". For example, to enable Block Storage service:

  .. code-block:: console

     enable_cinder: "yes"

  Kolla now supports many OpenStack services, there is
  `a list of available services
  <https://github.com/openstack/kolla-ansible/blob/master/README.rst#openstack-services>`_.
  For more information about service configuration, Please refer to the
  :kolla-ansible-doc:`Services Reference Guide
  <reference/index.html>`.

* Virtual environment

  It is recommended to use a virtual environment to execute tasks on the remote
  hosts.  This is covered
  :kolla-ansible-doc:`Virtual Environments <user/virtual-environments.html>`.

Deployment
~~~~~~~~~~

After configuration is set, we can proceed to the deployment phase. First we
need to setup basic host-level dependencies, like docker.

Kolla-Ansible provides a playbook that will install all required services in
the correct versions.

The following assumes the use of the ``multinode`` inventory. If using a
different inventory, such as ``all-in-one``, replace the ``-i`` argument
accordingly.

* For deployment or evaluation, run:

  #. Bootstrap servers with kolla deploy dependencies:

     .. code-block:: console

        kolla-ansible -i ./multinode bootstrap-servers

  #. Do pre-deployment checks for hosts:

     .. code-block:: console

        kolla-ansible -i ./multinode prechecks

  #. Finally proceed to actual OpenStack deployment:

     .. code-block:: console

        kolla-ansible -i ./multinode deploy

* For development, run:

  #. Bootstrap servers with kolla deploy dependencies:

     .. code-block:: console

        cd kolla-ansible/tools
        ./kolla-ansible -i ../../multinode bootstrap-servers

  #. Do pre-deployment checks for hosts:

     .. code-block:: console

        ./kolla-ansible -i ../../multinode prechecks

  #. Finally proceed to actual OpenStack deployment:

     .. code-block:: console

        ./kolla-ansible -i ../../multinode deploy

When this playbook finishes, OpenStack should be up, running and functional!
If error occurs during execution, refer to
:kolla-ansible-doc:`troubleshooting guide <user/troubleshooting.html>`.

Using OpenStack
~~~~~~~~~~~~~~~

#. Install the OpenStack CLI client:

   .. code-block:: console

      pip install python3-openstackclient

#. OpenStack requires an openrc file where credentials for admin user
   are set. To generate this file:

   * For deployment or evaluation, run:

     .. code-block:: console

        kolla-ansible post-deploy
        . /etc/kolla/admin-openrc.sh

   * For development, run:

     .. code-block:: console

        cd kolla-ansible/tools
        ./kolla-ansible post-deploy
        . /etc/kolla/admin-openrc.sh

#. Depending on how you installed Kolla-Ansible, there is a script that will
   create example networks, images, and so on.

   * For deployment or evaluation,
     run ``init-runonce`` script:

     .. code-block:: console

        /usr/local/share/kolla-ansible/init-runonce

   * For development, run:

     .. code-block:: console

        kolla-ansible/tools/init-runonce
