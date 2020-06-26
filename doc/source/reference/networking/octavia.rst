=======
Octavia
=======

Octavia provides load balancing as a service. This guide covers configuration
of Octavia for the Amphora driver. See the :octavia-doc:`Octavia documentation
<>` for full details. The :octavia-doc:`installation guide
<install/install-ubuntu.html>` is a useful reference.

Resources
=========

Currently in Kolla Ansible it is necessary to manually register the OpenStack
resources required by Octavia. Kolla Ansible aims to automate this in the
future.

.. note::

   In Train and earlier releases, resources should be registered in the
   ``admin`` project. This is configured via ``octavia_service_auth_project``,
   and may be set to ``service`` to avoid a breaking change when upgrading to
   Ussuri. Changing the project on an existing system requires at a minimum
   registering a new security group in the new project. Ideally the flavor and
   network should be recreated in the new project, although this will impact
   existing Amphorae.

All resources should be registered in the ``service`` project. This can be done
as follows:

.. code-block:: console

   source admin-openrc.sh
   export OS_USERNAME=octavia
   export OS_PASSWORD=<octavia keystone password>
   export OS_PROJECT_NAME=service
   export OS_TENANT_NAME=service

You can find the Octavia password in ``passwords.yml``.

Amphora image
-------------

It is necessary to build an Amphora image. On CentOS / RHEL 8:

.. code-block:: console

   sudo dnf -y install epel-release
   sudo dnf install -y debootstrap

On Ubuntu:

.. code-block:: console

   sudo apt -y install debootstrap

Acquire the Octavia source code:

.. code-block:: console

   git clone https://opendev.org/openstack/octavia -b <branch>

Install ``diskimage-builder``, ideally in a virtual environment:

.. code-block:: console

   python3 -m venv dib-venv
   source dib-venv/bin/activate
   pip install diskimage-builder

Create the Amphora image:

.. code-block:: console

   cd octavia/diskimage-create
   ./diskimage-create.sh

Register the image in Glance:

.. code-block:: console

   openstack image create amphora-x64-haproxy.qcow2 --container-format bare --disk-format qcow2 --private --tag amphora --file amphora-x64-haproxy.qcow2

Octavia uses the tag to determine which image to use.

Amphora flavor
--------------

Register the flavor in Nova:

.. code-block:: console

   openstack flavor create --vcpus 1 --ram 1024 --disk 2 "amphora" --private

Make a note of the ID of the flavor, or specify one via ``--id``.

Keypair
-------

Register the keypair in Nova:

.. code-block:: console

   openstack keypair create --public-key <path to octavia public key> octavia_ssh_key

Network and subnet
------------------

Register the management network and subnet in Neutron. This must be a network
that is accessible from the controllers. Typically a VLAN provider network is
used. In that case it will be necessary to enable Neutron provider networks.

.. code-block:: console

   OCTAVIA_MGMT_SUBNET=192.168.43.0/24
   OCTAVIA_MGMT_SUBNET_START=192.168.43.10
   OCTAVIA_MGMT_SUBNET_END=192.168.43.254

   openstack network create lb-mgmt-net --provider-network-type vlan --provider-segment 107  --provider-physical-network physnet1
   openstack subnet create --subnet-range $OCTAVIA_MGMT_SUBNET --allocation-pool \
     start=$OCTAVIA_MGMT_SUBNET_START,end=$OCTAVIA_MGMT_SUBNET_END \
     --network lb-mgmt-net lb-mgmt-subnet

Make a note of the ID of the network.

Security group
--------------

Register the security group in Neutron.

.. code-block:: console

   openstack security group create lb-mgmt-sec-grp
   openstack security group rule create --protocol icmp lb-mgmt-sec-grp
   openstack security group rule create --protocol tcp --dst-port 22 lb-mgmt-sec-grp
   openstack security group rule create --protocol tcp --dst-port 9443 lb-mgmt-sec-grp

Make a note of the ID of the security group.

Kolla Ansible configuration
===========================

Globals
-------

The following options should be added to ``globals.yml``.

Enable the Octavia service:

.. code-block:: yaml

   enable_octavia: yes

If using a VLAN for the Octavia management network, enable Neutron provider
networks:

.. code-block:: yaml

   enable_neutron_provider_networks: yes

Configure the name of the network interface on the controllers used to access
the Octavia management network. If using a VLAN provider network, ensure that
the traffic is also bridged to Open vSwitch on the controllers.

.. code-block:: yaml

   octavia_network_interface: <network interface on controllers>

Set the IDs of the resources registered previously:

.. code-block:: yaml

   octavia_amp_boot_network_list: <ID of lb-mgmt-net>
   octavia_amp_secgroup_list: <ID of lb-mgmt-sec-grp>
   octavia_amp_flavor_id: <ID of amphora flavor>

Passwords
---------

The following option should be set in ``passwords.yml``, matching the password
used to encrypt the CA key:

.. code-block:: yaml

   octavia_ca_password: <CA key password>

Certificates
============

Follow the :octavia-doc:`octavia documentation
<admin/guides/certificates.html>` to generate certificates for Amphorae. These
should be copied to the Kolla Ansible configuration as follows:

.. code-block:: ini

   cp client_ca/certs/ca.cert.pem /etc/kolla/config/octavia/client_ca.cert.pem
   cp server_ca/certs/ca.cert.pem /etc/kolla/config/octavia/server_ca.cert.pem
   cp server_ca/private/ca.key.pem /etc/kolla/config/octavia/server_ca.key.pem
   cp client_ca/private/client.cert-and-key.pem /etc/kolla/config/octavia/client.cert-and-key.pem
