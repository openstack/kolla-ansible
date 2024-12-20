===========================
Bifrost - Standalone Ironic
===========================

From the ``Bifrost`` developer documentation:
    Bifrost (pronounced bye-frost) is a set of Ansible playbooks that automates
    the task of deploying a base image onto a set of known hardware using
    Ironic.  It provides modular utility for one-off operating system
    deployment with as few operational requirements as reasonably possible.

Kolla uses bifrost as a mechanism for bootstrapping an OpenStack control plane
on a set of baremetal servers.  Kolla provides a container image for bifrost.
Kolla-ansible provides a playbook to configure and deploy the bifrost
container, as well as building a base OS image and provisioning it onto the
baremetal nodes.

Hosts in the System
~~~~~~~~~~~~~~~~~~~

In a system deployed by bifrost we define a number of classes of hosts.

Control host
    The control host is the host on which kolla and kolla-ansible will be
    installed, and is typically where the cloud will be managed from.
Deployment host
    The deployment host runs the bifrost deploy container and is used to
    provision the cloud hosts.
Cloud hosts
    The cloud hosts run the OpenStack control plane, compute and storage
    services.
Bare metal compute hosts:
    In a cloud providing bare metal compute services to tenants via Ironic,
    these hosts will run the bare metal tenant workloads.  In a cloud with only
    virtualised compute this category of hosts does not exist.

.. note::

   In many cases the control and deployment host will be the same, although
   this is not mandatory.

.. note::

   Bifrost supports provisioning of bare metal nodes.  While kolla-ansible is
   agnostic to whether the host OS runs on bare metal or is virtualised, in a
   virtual environment the provisioning of VMs for cloud hosts and their base
   OS images is currently out of scope.

Cloud Deployment Procedure
~~~~~~~~~~~~~~~~~~~~~~~~~~

Cloud deployment using kolla and bifrost follows the following high level
steps:

#. Install and configure kolla and kolla-ansible on the control host.
#. Deploy bifrost on the deployment host.
#. Use bifrost to build a base OS image and provision cloud hosts with this
   image.
#. Deploy OpenStack services on the cloud hosts provisioned by bifrost.

Preparation
~~~~~~~~~~~

Prepare the Control Host
------------------------

Follow the **Install dependencies** section of the :doc:`../../user/quickstart`
guide instructions to set up kolla and kolla-ansible dependencies.  Follow
the instructions in either the **Install kolla for development** section or
the **Install kolla for deployment or evaluation** section to install kolla
and kolla-ansible.

Prepare the Deployment Host
---------------------------

RabbitMQ requires that the system's hostname resolves to the IP address that it
has been configured to use, which with bifrost will be ``127.0.0.1``.  Bifrost
will attempt to modify ``/etc/hosts`` on the deployment host to ensure that
this is the case.  Docker bind mounts ``/etc/hosts`` into the container from a
volume.  This prevents atomic renames which will prevent Ansible from fixing
the ``/etc/hosts`` file automatically.

To enable bifrost to be bootstrapped correctly, add an entry to ``/etc/hosts``
resolving the deployment host's hostname to ``127.0.0.1``, for example:

.. code-block:: console

    cat /etc/hosts
    127.0.0.1 bifrost localhost

The following lines are desirable for IPv6 capable hosts:

.. code-block:: console

    ::1 ip6-localhost ip6-loopback
    fe00::0 ip6-localnet
    ff00::0 ip6-mcastprefix
    ff02::1 ip6-allnodes
    ff02::2 ip6-allrouters
    ff02::3 ip6-allhosts
    192.168.100.15 bifrost

Build a Bifrost Container Image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section provides instructions on how to build a container image for
bifrost using kolla.

Currently kolla only supports the ``source`` install type for the
bifrost image.

#. To generate kolla-build.conf configuration File


   * If required, generate a default configuration file for
     :command:`kolla-build`:

     .. code-block:: console

        cd kolla
        tox -e genconfig

Alternatively, instead of using ``kolla-build.conf``, a ``source`` build can
be enabled by appending ``--type source`` to the :command:`kolla-build` or
``tools/build.py`` command.

#. To build images, for Development:

   .. code-block:: console

      cd kolla
      tools/build.py bifrost-deploy

   For Production:

   .. code-block:: console

      kolla-build bifrost-deploy

   .. note::

      By default :command:`kolla-build` will build all containers using CentOS as
      the base image. To change this behavior, use the following parameter with
      :command:`kolla-build` or ``tools/build.py`` command:

      .. code-block:: console

         --base [centos|debian|rocky|ubuntu]

Configure and Deploy a Bifrost Container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section provides instructions for how to configure and deploy a container
running bifrost services.

Prepare Kolla Ansible Inventory
-------------------------------

Kolla-ansible will deploy bifrost on the hosts in the ``bifrost`` Ansible
group.  In the ``all-in-one`` and ``multinode`` inventory files, a ``bifrost``
group is defined which contains all hosts in the ``deployment`` group.  This
top level ``deployment`` group is intended to represent the host running the
``bifrost_deploy`` container.  By default, this group contains ``localhost``.
See :doc:`/user/multinode` for details on how to modify the Ansible inventory
in a multinode deployment.

Bifrost does not currently support running on multiple hosts so the ``bifrost``
group should contain only a single host, however this is not enforced by
kolla-ansible.  Bifrost manages a number of services that conflict with
services deployed by kolla including OpenStack Ironic, MariaDB, RabbitMQ and
(optionally) OpenStack Keystone.  These services should not be deployed on the
host on which bifrost is deployed.

Prepare Kolla Ansible Configuration
-----------------------------------

Follow the instructions in :doc:`../../user/quickstart` to prepare
kolla-ansible's global configuration file ``globals.yml``.  For bifrost, the
``bifrost_network_interface`` variable should be set to the name of the
interface that will be used to provision bare metal cloud hosts if this is
different than ``network_interface``.  For example to use ``eth1``:

.. code-block:: yaml

   bifrost_network_interface: eth1

Note that this interface should typically have L2 network connectivity with the
bare metal cloud hosts in order to provide DHCP leases with PXE boot options.

Prepare Bifrost Configuration
-----------------------------

Kolla ansible custom configuration files can be placed in a directory given by
the ``node_custom_config`` variable, which defaults do ``/etc/kolla/config``.
Bifrost configuration files should be placed in this directory or in a
``bifrost`` subdirectory of it (e.g. ``/etc/kolla/config/bifrost``). Within
these directories the files ``bifrost.yml``, ``servers.yml`` and ``dib.yml``
can be used to configure Bifrost.

Create a Bifrost Inventory
~~~~~~~~~~~~~~~~~~~~~~~~~~

The file ``servers.yml`` defines the bifrost hardware inventory that will be
used to populate Ironic.  See the `bifrost dynamic inventory examples
<https://github.com/openstack/bifrost/tree/master/playbooks/inventory>`_ for
further details.

For example, the following inventory defines a single node managed via the
Ironic ``ipmi`` driver.  The inventory contains credentials required
to access the node's BMC via IPMI, the MAC addresses of the node's NICs, an IP
address to configure the node's configdrive with, a set of scheduling
properties and a logical name.

.. code-block:: yaml

   ---
   cloud1:
     uuid: "31303735-3934-4247-3830-333132535336"
     driver_info:
       power:
         ipmi_username: "admin"
         ipmi_address: "192.168.1.30"
         ipmi_password: "root"
     nics:
       -
         mac: "1c:c1:de:1c:aa:53"
       -
         mac: "1c:c1:de:1c:aa:52"
     driver: "ipmi"
     ipv4_address: "192.168.1.10"
     properties:
       cpu_arch: "x86_64"
       ram: "24576"
       disk_size: "120"
       cpus: "16"
     name: "cloud1"

The required inventory will be specific to the hardware and environment in use.

Create Bifrost Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The file ``bifrost.yml`` provides global configuration for the bifrost
playbooks.  By default kolla mostly uses bifrost's default variable values.
For details on bifrost's variables see the bifrost documentation. For example:

.. code-block:: yaml

   mysql_service_name: mysql
   ansible_python_interpreter: /var/lib/kolla/venv/bin/python
   enabled_hardware_types: ipmi
   # uncomment below if needed
   # dhcp_pool_start: 192.168.2.200
   # dhcp_pool_end: 192.168.2.250
   # dhcp_lease_time: 12h
   # dhcp_static_mask: 255.255.255.0

Create Disk Image Builder Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The file ``dib.yml`` provides configuration for bifrost's image build
playbooks.  By default kolla mostly uses bifrost's default variable values when
building the baremetal OS and deployment images, and will build an
**Ubuntu-based** image for deployment to nodes.  For details on bifrost's
variables see the bifrost documentation.

For example, to use the ``debian`` Disk Image Builder OS element:

.. code-block:: yaml

   dib_os_element: debian

See the `diskimage-builder documentation
<https://docs.openstack.org/diskimage-builder/latest/>`__ for more details.

Deploy Bifrost
~~~~~~~~~~~~~~

The bifrost container can be deployed either using kolla-ansible or manually.

Deploy Bifrost using Kolla Ansible
----------------------------------

For development:

.. code-block:: console

   pip install -e ./kolla-ansible
   kolla-ansible deploy-bifrost


For Production:

.. code-block:: console

   pip install -U ./kolla-ansible
   kolla-ansible deploy-bifrost

Deploy Bifrost manually
-----------------------

#. Start Bifrost Container

   .. code-block:: console

      docker run -it --net=host -v /dev:/dev -d \
      --privileged --name bifrost_deploy \
      kolla/ubuntu-source-bifrost-deploy:3.0.1

#. Copy Configuration Files

   .. code-block:: console

      docker exec -it bifrost_deploy mkdir /etc/bifrost
      docker cp /etc/kolla/config/bifrost/servers.yml bifrost_deploy:/etc/bifrost/servers.yml
      docker cp /etc/kolla/config/bifrost/bifrost.yml bifrost_deploy:/etc/bifrost/bifrost.yml
      docker cp /etc/kolla/config/bifrost/dib.yml bifrost_deploy:/etc/bifrost/dib.yml

#. Bootstrap Bifrost

   .. code-block:: console

      docker exec -it bifrost_deploy bash

#. Generate an SSH Key

   .. code-block:: console

      ssh-keygen

#. Bootstrap and Start Services

   .. code-block:: console

      cd /bifrost
      ./scripts/env-setup.sh
      export OS_CLOUD=bifrost
      cat > /etc/rabbitmq/rabbitmq-env.conf << EOF
      HOME=/var/lib/rabbitmq
      EOF
      ansible-playbook -vvvv \
      -i /bifrost/playbooks/inventory/target \
      /bifrost/playbooks/install.yaml \
      -e @/etc/bifrost/bifrost.yml \
      -e @/etc/bifrost/dib.yml \
      -e skip_package_install=true

Validate the Deployed Container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

   docker exec -it bifrost_deploy bash
   cd /bifrost
   export OS_CLOUD=bifrost

Running "ironic node-list" should return with no nodes, for example

.. code-block:: console

   (bifrost-deploy)[root@bifrost bifrost]# ironic node-list
   +------+------+---------------+-------------+--------------------+-------------+
   | UUID | Name | Instance UUID | Power State | Provisioning State | Maintenance |
   +------+------+---------------+-------------+--------------------+-------------+
   +------+------+---------------+-------------+--------------------+-------------+

Enroll and Deploy Physical Nodes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once we have deployed a bifrost container we can use it to provision the bare
metal cloud hosts specified in the inventory file. Again, this can be done
either using kolla-ansible or manually.

By Kolla Ansible
----------------

For Development:


.. code-block:: console

   pip install -e ./kolla-ansible
   kolla-ansible deploy-servers

For Production:

.. code-block:: console

   pip install -U ./kolla-ansible
   kolla-ansible deploy-servers

Manually
--------

.. code-block:: console

   docker exec -it bifrost_deploy bash
   cd /bifrost
   export OS_CLOUD=bifrost
   export BIFROST_INVENTORY_SOURCE=/etc/bifrost/servers.yml
   ansible-playbook -vvvv \
   -i /bifrost/playbooks/inventory/bifrost_inventory.py \
   /bifrost/playbooks/enroll-dynamic.yaml \
   -e "ansible_python_interpreter=/var/lib/kolla/venv/bin/python" \
   -e @/etc/bifrost/bifrost.yml

   docker exec -it bifrost_deploy bash
   cd /bifrost
   export OS_CLOUD=bifrost
   export BIFROST_INVENTORY_SOURCE=/etc/bifrost/servers.yml
   ansible-playbook -vvvv \
   -i /bifrost/playbooks/inventory/bifrost_inventory.py \
   /bifrost/playbooks/deploy-dynamic.yaml \
   -e "ansible_python_interpreter=/var/lib/kolla/venv/bin/python" \
   -e @/etc/bifrost/bifrost.yml

At this point Ironic should clean down the nodes and install the default
OS image.

Advanced Configuration
~~~~~~~~~~~~~~~~~~~~~~

Bring Your Own Image
--------------------

TODO

Bring Your Own SSH Key
----------------------

To use your own SSH key after you have generated the ``passwords.yml`` file
update the private and public keys under ``bifrost_ssh_key``.

Known issues
~~~~~~~~~~~~

SSH daemon not running
----------------------

By default ``sshd`` is installed in the image but may not be enabled.  If you
encounter this issue you will have to access the server physically in recovery
mode to enable the ``sshd`` service. If your hardware supports it, this can be
done remotely with :command:`ipmitool` and Serial Over LAN. For example

.. code-block:: console

   ipmitool -I lanplus -H 192.168.1.30 -U admin -P root sol activate

References
~~~~~~~~~~

* :bifrost-doc:`Bifrost documentation <>`

* :bifrost-doc:`Bifrost troubleshooting guide <user/troubleshooting.html>`

* `Bifrost code repository <https://github.com/openstack/bifrost>`__

