====================================
Development Environment with Vagrant
====================================

This guide describes how to use `Vagrant <https://vagrantup.com>`__ to assist in
developing for Kolla.

Vagrant is a tool for building and managing virtual machine environments in
a single workflow. Vagrant takes care of setting up CentOS-based VMs for Kolla
development, each with proper hardware like memory amount and number of
network interfaces.

Getting Started
===============

The Vagrant script implements **all-in-one** or **multi-node** deployments.
**all-in-one** is the default.

In the case of **multi-node** deployment, the Vagrant setup builds a cluster
with the following nodes by default:

*  3 control nodes
*  1 compute node
*  1 storage node (Note: ceph requires at least 3 storage nodes)
*  1 network node
*  1 operator node

The cluster node count can be changed by editing the Vagrantfile.

Kolla runs from the operator node to deploy OpenStack.

All nodes are connected with each other on the secondary NIC. The primary NIC
is behind a NAT interface for connecting with the Internet. The third NIC is
connected without IP configuration to a public bridge interface. This may be
used for Neutron/Nova to connect to instances.

Start by downloading and installing the Vagrant package for the distro of
choice. Various downloads can be found at the `Vagrant downloads
<https://www.vagrantup.com/downloads.html>`__.

Install required dependencies as follows:

For CentOS or RHEL 8:

.. code-block:: console

   sudo dnf install ruby-devel libvirt-devel zlib-devel libpng-devel gcc \
   qemu-kvm qemu-img libvirt python3-libvirt libvirt-client virt-install git

For Ubuntu 16.04 or later:

.. code-block:: console

   sudo apt install vagrant ruby-dev ruby-libvirt python-libvirt \
   qemu-utils qemu-kvm libvirt-dev nfs-kernel-server zlib1g-dev libpng12-dev \
   gcc git

.. note::

   Many distros ship outdated versions of Vagrant by default. When in
   doubt, always install the latest from the downloads page above.

Next install the hostmanager plugin so all hosts are recorded in ``/etc/hosts``
(inside each vm):

.. code-block:: console

   vagrant plugin install vagrant-hostmanager

Vagrant supports a wide range of virtualization technologies. If VirtualBox is
used, the vbguest plugin will be required to install the VirtualBox Guest
Additions in the virtual machine:

.. code-block:: console

   vagrant plugin install vagrant-vbguest

This documentation focuses on libvirt specifics. To install vagrant-libvirt
plugin:

.. code-block:: console

   vagrant plugin install --plugin-version ">= 0.0.31" vagrant-libvirt

Some Linux distributions offer vagrant-libvirt packages, but the version they
provide tends to be too old to run Kolla. A version of >= 0.0.31 is required.

To use libvirt from Vagrant with a low privileges user without being asked for
a password, add the user to the libvirt group:

.. code-block:: console

   sudo gpasswd -a ${USER} libvirt
   newgrp libvirt

.. note::

   In Ubuntu 16.04 and later, libvirtd group is used.

Setup NFS to permit file sharing between host and VMs. Contrary to the rsync
method, NFS allows both way synchronization and offers much better performance
than VirtualBox shared folders. For CentOS:

#. Add the virtual interfaces to the internal zone:

.. code-block:: console

   sudo firewall-cmd --zone=internal --add-interface=virbr0
   sudo firewall-cmd --zone=internal --add-interface=virbr1

#. Enable nfs, rpc-bind and mountd services for firewalld:

.. code-block:: console

   sudo firewall-cmd --permanent --zone=internal --add-service=nfs
   sudo firewall-cmd --permanent --zone=internal --add-service=rpc-bind
   sudo firewall-cmd --permanent --zone=internal --add-service=mountd
   sudo firewall-cmd --permanent --zone=internal --add-port=2049/udp
   sudo firewall-cmd --permanent --add-port=2049/tcp
   sudo firewall-cmd --permanent --add-port=111/udp
   sudo firewall-cmd --permanent --add-port=111/tcp
   sudo firewall-cmd --reload

.. note::

   You may not have to do this because Ubuntu uses Uncomplicated Firewall (ufw)
   and ufw is disabled by default.

#. Start required services for NFS:

.. code-block:: console

   sudo systemctl restart firewalld
   sudo systemctl start nfs-server
   sudo systemctl start rpcbind.service

Ensure your system has libvirt and associated software installed and setup
correctly. For CentOS:

.. code-block:: console

   sudo systemctl start libvirtd
   sudo systemctl enable libvirtd

Find a location in the system's home directory and checkout Kolla repos:

.. code-block:: console

   git clone https://opendev.org/openstack/kolla-cli
   git clone https://opendev.org/openstack/kolla-ansible
   git clone https://opendev.org/openstack/kolla

All repos must share the same parent directory so the bootstrap code can
locate them.

Developers can now tweak the Vagrantfile or bring up the default **all-in-one**
CentOS 7-based environment:

.. code-block:: console

   cd kolla-ansible/contrib/dev/vagrant && vagrant up

The command ``vagrant status`` provides a quick overview of the VMs composing
the environment.

Vagrant Up
==========

Once Vagrant has completed deploying all nodes, the next step is to launch
Kolla. First, connect with the **operator** node:

.. code-block:: console

   vagrant ssh operator

To speed things up, there is a local registry running on the operator. All
nodes are configured so they can use this insecure repo to pull from, and use
it as a mirror. Ansible may use this registry to pull images from.

All nodes have a local folder shared between the group and the hypervisor, and
a folder shared between **all** nodes and the hypervisor. This mapping is lost
after reboots, so make sure to use the command ``vagrant reload <node>`` when
reboots are required. Having this shared folder provides a method to supply
a different Docker binary to the cluster. The shared folder is also used to
store the docker-registry files, so they are save from destructive operations
like ``vagrant destroy``.

Building images
---------------

Once logged on the **operator** VM call the ``kolla-build`` utility:

.. code-block:: console

   kolla-build

``kolla-build`` accept arguments as documented in
:kolla-doc:`Building Container Images <admin/image-building.html>`.
It builds Docker images and pushes them to the local registry if the **push**
option is enabled (in Vagrant this is the default behaviour).

Generating passwords
--------------------

Before proceeding with the deployment you must generate the service passwords:

.. code-block:: console

   kolla-genpwd

Deploying OpenStack with Kolla
------------------------------

To deploy **all-in-one**:

.. code-block:: console

   sudo kolla-ansible deploy

To deploy **multinode**:

Ensure that the nodes deployed by Vagrant match those specified in the
inventory file:
``/usr/share/kolla-ansible/ansible/inventory/multinode``.

For Centos 7:

.. code-block:: console

   sudo kolla-ansible deploy -i /usr/share/kolla-ansible/ansible/inventory/multinode

For Ubuntu 16.04 or later:

.. code-block:: console

   sudo kolla-ansible deploy -i /usr/local/share/kolla-ansible/ansible/inventory/multinode

Validate OpenStack is operational:

.. code-block:: console

   kolla-ansible post-deploy
   export OS_CLIENT_CONFIG_FILE=/etc/kolla/clouds.yaml
   export OS_CLOUD=kolla-admin
   openstack user list

Or navigate to ``http://172.28.128.254/`` with a web browser.

Further Reading
===============

All Vagrant documentation can be found at
`Vagrant documentation <https://www.vagrantup.com/docs/>`_.

