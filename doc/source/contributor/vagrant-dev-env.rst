.. vagrant-dev-env:

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

On CentOS::

  sudo yum install ruby-devel libvirt-devel zlib-devel libpng-devel gcc \
  qemu-kvm qemu-img libvirt libvirt-python libvirt-client virt-install \
  bridge-utils git

On Ubuntu 16.04 or later::

  sudo apt-get install vagrant ruby-dev ruby-libvirt python-libvirt libvirt-dev nfs-kernel-server zlib1g-dev libpng12-dev gcc git

.. note:: Many distros ship outdated versions of Vagrant by default. When in
          doubt, always install the latest from the downloads page above.

Next install the hostmanager plugin so all hosts are recorded in ``/etc/hosts``
(inside each vm)::

  vagrant plugin install vagrant-hostmanager

If you are going to use VirtualBox, then install vagrant-vbguest::

  vagrant plugin install vagrant-vbguest

Vagrant supports a wide range of virtualization technologies. If VirtualBox is
used, the vbguest plugin will be required to install the VirtualBox Guest
Additions in the virtual machine::

    vagrant plugin install vagrant-vbguest

This documentation focuses on libvirt specifics. To install vagrant-libvirt
plugin::

  vagrant plugin install --plugin-version ">= 0.0.31" vagrant-libvirt

Some Linux distributions offer vagrant-libvirt packages, but the version they
provide tends to be too old to run Kolla. A version of >= 0.0.31 is required.

To use libvirt from Vagrant with a low privileges user without being asked for
a password, add the user to the libvirt group::

  sudo gpasswd -a ${USER} libvirt
  newgrp libvirt

Setup NFS to permit file sharing between host and VMs. Contrary to the rsync
method, NFS allows both way synchronization and offers much better performance
than VirtualBox shared folders. On CentOS::

    # Add the virtual interfaces to the internal zone
    sudo firewall-cmd --zone=internal --add-interface=virbr0
    sudo firewall-cmd --zone=internal --add-interface=virbr1
    # Enable nfs, rpc-bind and mountd services for firewalld
    sudo firewall-cmd --permanent --zone=internal --add-service=nfs
    sudo firewall-cmd --permanent --zone=internal --add-service=rpc-bind
    sudo firewall-cmd --permanent --zone=internal --add-service=mountd
    sudo firewall-cmd --permanent --zone=internal --add-port=2049/udp
    sudo firewall-cmd --permanent --add-port=2049/tcp
    sudo firewall-cmd --permanent --add-port=111/udp
    sudo firewall-cmd --permanent --add-port=111/tcp
    sudo firewall-cmd --reload
    # Start required services for NFS
    sudo systemctl restart firewalld
    sudo systemctl start nfs-server
    sudo systemctl start rpcbind.service

Ensure your system has libvirt and associated software installed and setup
correctly. On CentOS::

    sudo systemctl start libvirtd
    sudo systemctl enable libvirtd

Find a location in the system's home directory and checkout Kolla repos::

    git clone https://git.openstack.org/openstack/kolla-ansible
    git clone https://git.openstack.org/openstack/kolla

Both repos must share the same parent directory so the bootstrap code can
locate them.

Developers can now tweak the Vagrantfile or bring up the default **all-in-one**
CentOS 7-based environment::

    cd kolla-ansible/contrib/dev/vagrant && vagrant up

The command ``vagrant status`` provides a quick overview of the VMs composing
the environment.

Vagrant Up
==========

Once Vagrant has completed deploying all nodes, the next step is to launch
Kolla. First, connect with the **operator** node::

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

Once logged on the **operator** VM call the ``kolla-build`` utility::

    kolla-build

``kolla-build`` accept arguments as documented in `Building Container Images`_.
It builds Docker images and pushes them to the local registry if the **push**
option is enabled (in Vagrant this is the default behaviour).

Deploying OpenStack with Kolla
------------------------------

Deploy **all-in-one** with::

    sudo kolla-ansible deploy

Deploy multinode
On Centos 7::

    sudo kolla-ansible deploy -i /usr/share/kolla-ansible/ansible/inventory/multinode

On Ubuntu 16.04 or later::

    sudo kolla-ansible deploy -i /usr/local/share/kolla-ansible/ansible/inventory/multinode

Validate OpenStack is operational::

    kolla-ansible post-deploy
    . /etc/kolla/admin-openrc.sh
    openstack user list

Or navigate to http://172.28.128.254/ with a web browser.

Further Reading
===============

All Vagrant documentation can be found at
`Vagrant documentation` <https://www.vagrantup.com/docs/>`__.

.. _Building Container Images: https://docs.openstack.org/kolla/latest/admin/image-building.html
