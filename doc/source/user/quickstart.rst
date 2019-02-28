.. quickstart:

===========
Quick Start
===========

This guide provides step by step instructions to deploy OpenStack using Kolla
on bare metal servers or virtual machines.

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

Install dependencies
~~~~~~~~~~~~~~~~~~~~

#. Install and upgrad ``pip`` to the latest before proceeding.

   For CentOS, run:

   .. code-block:: console

      yum install epel-release
      yum install python-pip
      pip install -U pip

   For Ubuntu, run:

   .. code-block:: console

      apt-get update
      apt-get install python-pip
      pip install -U pip

#. Install the following dependencies:

   For CentOS, run:

   .. code-block:: console

      yum install python-devel libffi-devel gcc openssl-devel libselinux-python

   For Ubuntu, run:

   .. code-block:: console

      apt-get install python-dev libffi-dev gcc libssl-dev python-selinux python-setuptools

#. Install `Ansible <http://www.ansible.com>`__ from distribution packaging:

   .. note::

      Some implemented distro versions of Ansible are too old to use distro
      packaging. Currently, CentOS and RHEL package Ansible >=2.4 which is suitable
      for use with Kolla. Note that you will need to enable access to the EPEL
      repository to install via :command:`yum` to do so, take a look at `Fedora's EPEL docs
      <https://fedoraproject.org/wiki/EPEL>`__ and `FAQ
      <https://fedoraproject.org/wiki/EPEL/FAQ>`__.

   For CentOS or RHEL, this can be done using:

   .. code-block:: console

      yum install ansible

   For Ubuntu, it can be installed by:

   .. code-block:: console

      apt-get install ansible

#. Use ``pip`` to install or upgrade Ansible to latest version:

   .. code-block:: console

      pip install -U ansible

   .. note::

      It is recommended to use virtualenv to install non-system packages.

#. (optional) Add the following options to ansible configuration file
   ``/etc/ansible/ansible.cfg``:

   .. path /etc/ansible/ansible.cfg
   .. code-block:: ini

      [defaults]
      host_key_checking=False
      pipelining=True
      forks=100

Install Kolla-ansible
~~~~~~~~~~~~~~~~~~~~~

Install Kolla-ansible for deployment or evaluation
--------------------------------------------------

#. Install kolla-ansible and its dependencies using ``pip``.

   .. code-block:: console

      pip install kolla-ansible

#. Copy ``globals.yml`` and ``passwords.yml`` to ``/etc/kolla`` directory.

   For CentOS, run:

   .. code-block:: console

      cp -r /usr/share/kolla-ansible/etc_examples/kolla /etc/

   For Ubuntu, run:

   .. code-block:: console

      cp -r /usr/local/share/kolla-ansible/etc_examples/kolla /etc/

#. Copy ``all-in-one`` and ``multinode`` inventory files to
   the current directory.

   For CentOS, run:

   .. code-block:: console

      cp /usr/share/kolla-ansible/ansible/inventory/* .

   For Ubuntu, run:

   .. code-block:: console

      cp /usr/local/share/kolla-ansible/ansible/inventory/* .

Install Kolla for development
-----------------------------

#. Clone ``kolla`` and ``kolla-ansible`` repositories from git.

   .. code-block:: console

      git clone https://github.com/openstack/kolla
      git clone https://github.com/openstack/kolla-ansible

#. Install requirements of ``kolla`` and ``kolla-ansible``:

   .. code-block:: console

      pip install -r kolla/requirements.txt
      pip install -r kolla-ansible/requirements.txt

#. Copy the configuration files to ``/etc/kolla`` directory.
   ``kolla-ansible`` holds the configuration files ( ``globals.yml`` and
   ``passwords.yml``) in ``etc/kolla``.

   .. code-block:: console

      mkdir -p /etc/kolla
      cp -r kolla-ansible/etc/kolla/* /etc/kolla

#. Copy the inventory files to the current directory. ``kolla-ansible`` holds
   inventory files ( ``all-in-one`` and ``multinode``) in the
   ``ansible/inventory`` directory.

   .. code-block:: console

      cp kolla-ansible/ansible/inventory/* .

Prepare initial configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inventory
---------

Next step is to prepare our inventory file. Inventory is an ansible file where
we specify node roles and access credentials.

Kolla-Ansible comes with ``all-in-one`` and ``multinode`` example inventory
files. Difference between them is that the former is ready for deploying
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

      Ubuntu might not come with python pre-installed. That will cause
      errors in ping module. To quickly install python with ansible you
      can run ``ansible -i multinode all -m raw -a "apt-get -y install python-dev"``

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
  mechanism, please refer `image building documentation
  <https://docs.openstack.org/kolla/latest/admin/image-building.html>`_.

  Kolla provides choice of several Linux distributions in containers:

  - Centos
  - Ubuntu
  - Oraclelinux
  - Debian
  - RHEL

  For newcomers, we recommend to use CentOS 7 or Ubuntu 16.04.

  .. code-block:: console

     kolla_base_distro: "centos"

  Next "type" of installation needs to be configured.
  Choices are:

  binary
   using repositories like apt or yum

  source
   using raw source archives, git repositories or local source directory

  .. note::

     This only affects OpenStack services. Infrastructure services like Ceph are
     always "binary".

  .. note::

     Source builds are proven to be slightly more reliable than binary.

  .. code-block:: console

     kolla_install_type: "source"

  To use DockerHub images, the default image tag has to be overridden. Images are
  tagged with release names. For example to use stable Rocky images set

  .. code-block:: console

     openstack_release: "rocky"

  It's important to use same version of images as kolla-ansible. That
  means if pip was used to install kolla-ansible, that means it's latest stable
  version so ``openstack_release`` should be set to rocky. If git was used with
  master branch, DockerHub also provides daily builds of master branch (which is
  tagged as ``master``):

  .. code-block:: console

     openstack_release: "master"

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

  To learn more about network configuration, refer `Network overview
  <https://docs.openstack.org/kolla-ansible/latest/admin/production-architecture-guide.html#network-configuration>`_.

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
  `Services Reference Guide
  <https://docs.openstack.org/kolla-ansible/latest/reference/index.html>`_.

Deployment
~~~~~~~~~~

After configuration is set, we can proceed to the deployment phase. First we
need to setup basic host-level dependencies, like docker.

Kolla-Ansible provides a playbook that will install all required services in
the correct versions.

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
        ./kolla-ansible -i ../ansible/inventory/multinode bootstrap-servers

  #. Do pre-deployment checks for hosts:

     .. code-block:: console

        ./kolla-ansible -i ../ansible/inventory/multinode prechecks

  #. Finally proceed to actual OpenStack deployment:

     .. code-block:: console

        ./kolla-ansible -i ../ansible/inventory/multinode deploy

When this playbook finishes, OpenStack should be up, running and functional!
If error occurs during execution, refer to
`troubleshooting guide <https://docs.openstack.org/kolla-ansible/latest/user/troubleshooting.html>`_.

Using OpenStack
~~~~~~~~~~~~~~~

#. Install basic OpenStack CLI clients:

   .. code-block:: console

      pip install python-openstackclient python-glanceclient python-neutronclient

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
     run ``init-runonce`` script on CentOS:

     .. code-block:: console

        . /usr/share/kolla-ansible/init-runonce

     Run ``init-runonce`` script on Ubuntu:

     .. code-block:: console

        . /usr/local/share/kolla-ansible/init-runonce

   * For development, run:

     .. code-block:: console

        . kolla-ansible/tools/init-runonce

