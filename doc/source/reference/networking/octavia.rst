=======
Octavia
=======

Octavia provides load balancing as a service. This guide covers configuration
of Octavia for the Amphora driver. See the :octavia-doc:`Octavia documentation
<>` for full details. The :octavia-doc:`installation guide
<install/install-ubuntu.html>` is a useful reference.

Enabling Octavia
================

Enable the octavia service in ``globals.yml``:

.. code-block:: yaml

   enable_octavia: "yes"

Certificates
============

Octavia requires various TLS certificates for operation. Since the Victoria
release, Kolla Ansible supports generating these certificates automatically.

Option 1: Automatically generating Certificates
-----------------------------------------------

Kolla Ansible provides default values for the certificate issuer and owner
fields. You can customize this via ``globals.yml``, for example:

.. code-block:: yaml

   octavia_certs_country: US
   octavia_certs_state: Oregon
   octavia_certs_organization: OpenStack
   octavia_certs_organizational_unit: Octavia

Generate octavia certificates:

.. code-block:: console

   kolla-ansible octavia-certificates

The certificates and keys will be generated under
``/etc/kolla/config/octavia``.

Option 2: Manually generating certificates
------------------------------------------

Follow the :octavia-doc:`octavia documentation
<admin/guides/certificates.html>` to generate certificates for Amphorae. These
should be copied to the Kolla Ansible configuration as follows:

.. code-block:: ini

   cp client_ca/certs/ca.cert.pem /etc/kolla/config/octavia/client_ca.cert.pem
   cp server_ca/certs/ca.cert.pem /etc/kolla/config/octavia/server_ca.cert.pem
   cp server_ca/private/ca.key.pem /etc/kolla/config/octavia/server_ca.key.pem
   cp client_ca/private/client.cert-and-key.pem /etc/kolla/config/octavia/client.cert-and-key.pem

The following option should be set in ``passwords.yml``, matching the password
used to encrypt the CA key:

.. code-block:: yaml

   octavia_ca_password: <CA key password>

.. _octavia-network:

Networking
==========

Octavia worker and health manager nodes must have access to the Octavia
management network for communication with Amphorae.

If using a VLAN for the Octavia management network, enable Neutron provider
networks:

.. code-block:: yaml

   enable_neutron_provider_networks: yes

Configure the name of the network interface on the controllers used to access
the Octavia management network. If using a VLAN provider network, ensure that
the traffic is also bridged to Open vSwitch on the controllers.

.. code-block:: yaml

   octavia_network_interface: <network interface on controllers>

This interface should have an IP address on the Octavia management subnet.

Registering OpenStack resources
===============================

Since the Victoria release, there are two ways to configure Octavia.

1. Kolla Ansible automatically registers resources for Octavia during
   deployment
2. Operator registers resources for Octavia after it is deployed

The first option is simpler, and is recommended for new users. The second
option provides more flexibility, at the cost of complexity for the operator.

Option 1: Automatic resource registration (default, recommended)
================================================================

For automatic resource registration, Kolla Ansible will register the following
resources:

* Nova flavor
* Nova SSH keypair
* Neutron network and subnet
* Neutron security groups

The configuration for these resources may be customised before deployment.

Customize Amphora flavor
------------------------

The default amphora flavor is named ``amphora`` with 1 VCPUs, 1GB RAM and 5GB
disk. you can customize this flavor by changing ``octavia_amphora_flavor``  in
``globals.yml``

See the ``os_nova_flavor`` Ansible module for details. Supported parameters
are:

- ``disk``
- ``ephemeral`` (optional)
- ``extra_specs`` (optional)
- ``flavorid`` (optional)
- ``is_public`` (optional)
- ``name``
- ``ram``
- ``swap`` (optional)
- ``vcpus``

The following defaults are used:

.. code-block:: yaml

   octavia_amp_flavor:
     name: "amphora"
     is_public: no
     vcpus: 1
     ram: 1024
     disk: 5

Customise network and subnet
----------------------------

Configure octavia management network and subnet in ``globals.yml``. This must
be a network that is :ref:`accessible from the controllers
<octavia-network>`. Typically a VLAN provider network is used.

See the ``os_network`` and ``os_subnet`` Ansible modules for details. Supported
parameters:

The network parameter has the following supported parameters:

- ``external`` (optional)
- ``mtu`` (optional)
- ``name``
- ``provider_network_type`` (optional)
- ``provider_physical_network`` (optional)
- ``provider_segmentation_id`` (optional)
- ``shared`` (optional)
- ``subnet``

The subnet parameter has the following supported parameters:

- ``allocation_pool_start`` (optional)
- ``allocation_pool_end`` (optional)
- ``cidr``
- ``enable_dhcp`` (optional)
- ``gateway_ip`` (optional)
- ``name``
- ``no_gateway_ip`` (optional)

For example:

.. code-block:: yaml

   octavia_amp_network:
     name: lb-mgmt-net
     provider_network_type: vlan
     provider_segmentation_id: 1000
     provider_physical_network: physnet1
     external: false
     shared: false
     subnet:
       name: lb-mgmt-subnet
       cidr: "10.1.2.0/24"
       allocation_pool_start: "10.1.2.100"
       allocation_pool_end: "10.1.2.200"
       gateway_ip: "10.1.2.1"
       enable_dhcp: yes

Deploy Octavia with Kolla Ansible:

.. code-block:: console

   kolla-ansible -i <inventory> deploy --tags common,horizon,octavia

Once the installation is completed, you need to :ref:`register an amphora image
in glance <octavia-amphora-image>`.

Option 2: Manual resource registration
======================================

In this case, Kolla Ansible will not register resources for Octavia. Set
``octavia_auto_configure`` to no in ``globals.yml``:

.. code-block:: yaml

   octavia_auto_configure: no

All resources should be registered in the ``service`` project. This can be done
as follows:

.. code-block:: console

   . /etc/kolla/octavia-openrc.sh

.. note::

   Ensure that you have executed ``kolla-ansible post-deploy`` and set
   ``enable_octavia`` to yes in ``global.yml``

.. note::

   In Train and earlier releases, resources should be registered in the
   ``admin`` project. This is configured via ``octavia_service_auth_project``,
   and may be set to ``service`` to avoid a breaking change when upgrading to
   Ussuri. Changing the project on an existing system requires at a minimum
   registering a new security group in the new project. Ideally the flavor and
   network should be recreated in the new project, although this will impact
   existing Amphorae.

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
that is :ref:`accessible from the controllers <octavia-network>`. Typically
a VLAN provider network is used.

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
---------------------------

The following options should be added to ``globals.yml``.

Set the IDs of the resources registered previously:

.. code-block:: yaml

   octavia_amp_boot_network_list: <ID of lb-mgmt-net>
   octavia_amp_secgroup_list: <ID of lb-mgmt-sec-grp>
   octavia_amp_flavor_id: <ID of amphora flavor>

Now deploy Octavia:

.. code-block:: console

   kolla-ansible -i <inventory> deploy --tags common,horizon,octavia

.. _octavia-amphora-image:

Amphora image
=============

It is necessary to build an Amphora image. On CentOS / RHEL 8:

.. code-block:: console

   sudo dnf -y install epel-release
   sudo dnf install -y debootstrap qemu-img git e2fsprogs policycoreutils-python-utils

On Ubuntu:

.. code-block:: console

   sudo apt -y install debootstrap qemu-utils git kpartx

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

Source octavia user openrc:

.. code-block:: console

   . /etc/kolla/octavia-openrc.sh

.. note::

   Ensure that you have executed ``kolla-ansible post-deploy``

Register the image in Glance:

.. code-block:: console

   openstack image create amphora-x64-haproxy.qcow2 --container-format bare --disk-format qcow2 --private --tag amphora --file amphora-x64-haproxy.qcow2 --property hw_architecture='x86_64' --property hw_rng_model=virtio

.. note::

   the tag should match the ``octavia_amp_image_tag`` in ``/etc/kolla/globals.yml``, by default,
   the tag is "amphora", octavia uses the tag to determine which image to use.

Debug
=====

SSH to an amphora
-----------------

login into one of octavia-worker nodes, and ssh into amphora.

.. code-block:: console

   ssh -i /etc/kolla/octavia-worker/octavia_ssh_key ubuntu@<amphora_ip>

.. note::

   amphora private key is located at ``/etc/kolla/octavia-worker/octavia_ssh_key`` on all
   octavia-worker nodes.

Upgrade
=======

If you upgrade from the Ussuri release, you must disable
``octavia_auto_configure`` in ``globals.yml`` and keep your other octavia
config as before.
