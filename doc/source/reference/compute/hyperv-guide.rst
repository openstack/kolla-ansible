.. _hyperv-guide:

===========
Nova HyperV
===========

Overview
~~~~~~~~
Currently, Kolla can deploy the following OpenStack services for Hyper-V:

* nova-compute
* neutron-hyperv-agent
* wsgate

It is possible to use Hyper-V as a compute node within an OpenStack Deployment.
The nova-compute service runs as openstack-compute, a 64-bit service directly
upon the Windows platform with the Hyper-V role enabled. The necessary Python
components as well as the nova-compute service are installed directly onto
the Windows platform. Windows Clustering Services are not needed for
functionality within the OpenStack infrastructure.

The wsgate is the FreeRDP-WebConnect service that is used for accessing
virtual machines from Horizon web interface.

.. note::

   HyperV services are not currently deployed as containers. This functionality
   is in development. The current implementation installs OpenStack services
   via MSIs.


.. note::

   HyperV services do not currently support outside the box upgrades. Manual
   upgrades are required for this process. MSI release versions can be found
   `here <https://cloudbase.it/openstack-hyperv-driver/>`__.
   To upgrade an existing MSI to a newer version, simply uninstall the current
   MSI and install the newer one. This will not delete the configuration files.
   To preserve the configuration files, check the Skip configuration checkbox
   during installation.


Preparation for Hyper-V node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ansible communicates with Hyper-V host via WinRM protocol. An HTTPS WinRM
listener needs to be configured on the Hyper-V host, which can be easily
created with `this PowerShell script
<https://github.com/ansible/ansible/blob/devel/examples/scripts/ConfigureRemotingForAnsible.ps1>`__.


A virtual switch has to be created with which Hyper-V virtual machines
communicate with OpenStack. To quickly enable an interface to be used as a
Virtual Interface the following PowerShell may be used:

.. code-block:: console

   PS C:\> $if = Get-NetIPAddress -IPAddress 192* | Get-NetIPInterface
   PS C:\> New-VMSwitch -NetAdapterName $if.ifAlias -Name YOUR_BRIDGE_NAME -AllowManagementOS $false

.. note::

   It is very important to make sure that when you are using a Hyper-V node
   with only 1 NIC the ``-AllowManagementOS`` option is set on ``True``,
   otherwise you will lose connectivity to the Hyper-V node.


To prepare the Hyper-V node to be able to attach to volumes provided by
cinder you must first make sure the Windows iSCSI initiator service is
running and started automatically.

.. code-block:: console

   PS C:\> Set-Service -Name MSiSCSI -StartupType Automatic
   PS C:\> Start-Service MSiSCSI

Preparation for Kolla deployer node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hyper-V role is required, enable it in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_hyperv: "yes"

Hyper-V options are also required in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   hyperv_username: <HyperV username>
   hyperv_password: <HyperV password>
   vswitch_name: <HyperV virtual switch name>
   nova_msi_url: "https://www.cloudbase.it/downloads/HyperVNovaCompute_Beta.msi"

If tenant networks are to be built using VLAN add corresponding type in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   neutron_tenant_network_types: 'flat,vlan'

The virtual switch is the same one created on the HyperV setup part.
For nova_msi_url, different Nova MSI (Mitaka/Newton/Ocata) versions can
be found on `Cloudbase website
<https://cloudbase.it/openstack-hyperv-driver/>`__.

Add the Hyper-V node in ``ansible/inventory`` file:

.. code-block:: ini

   [hyperv]
   <HyperV IP>

   [hyperv:vars]
   ansible_user=<HyperV user>
   ansible_password=<HyperV password>
   ansible_port=5986
   ansible_connection=winrm
   ansible_winrm_server_cert_validation=ignore

``pywinrm`` package needs to be installed in order for Ansible to work
on the HyperV node:

.. code-block:: console

   pip install "pywinrm>=0.2.2"

.. note::

   In case of a test deployment with controller and compute nodes as
   virtual machines on Hyper-V, if VLAN tenant networking is used,
   trunk mode has to be enabled on the VMs:

.. code-block:: console

   Set-VMNetworkAdapterVlan -Trunk -AllowedVlanIdList <VLAN ID> -NativeVlanId 0 <VM name>

networking-hyperv mechanism driver is needed for neutron-server to
communicate with HyperV nova-compute. This can be built with source
images by default. Manually it can be intalled in neutron-server
container with pip:

.. code-block:: console

   pip install "networking-hyperv>=4.0.0"

For neutron_extension_drivers, ``port_security`` and ``qos`` are
currently supported by the networking-hyperv mechanism driver.
By default only ``port_security`` is set.


Verify Operations
~~~~~~~~~~~~~~~~~

OpenStack HyperV services can be inspected and managed from PowerShell:

.. code-block:: console

   PS C:\> Get-Service nova-compute
   PS C:\> Get-Service neutron-hyperv-agent

.. code-block:: console

   PS C:\> Restart-Service nova-compute
   PS C:\> Restart-Service neutron-hyperv-agent

For more information on OpenStack HyperV, see
`Hyper-V virtualization platform
<https://docs.openstack.org/nova/latest/admin/configuration/hypervisor-hyper-v.html>`__.
