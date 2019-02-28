.. _vmware-guide:

======
VMware
======

Overview
~~~~~~~~

Kolla can deploy the Nova and Neutron Service(s) for VMware vSphere.
Depending on the network architecture (NsxV or DVS) you choose, Kolla deploys
the following OpenStack services for VMware vSphere:

For VMware NsxV:

* nova-compute
* neutron-server

For VMware DVS:

* nova-compute
* neutron-server
* neutron-dhcp-agent
* neutron-metadata-agent

Kolla can deploy the Glance and Cinder services using VMware datastore as their
backend. Ceilometer metering for vSphere is also supported.

Because the `vmware-nsx <https://github.com/openstack/vmware-nsx>`__ drivers for
neutron use completely different architecture than other types of
virtualization, vmware-nsx drivers cannot coexist with other type
of virtualization in one region. In neutron vmware-nsx drivers,
neutron-server acts like an agent to translate OpenStack actions
into what vSphere/NSX Manager API can understand. Neutron does
not directly takes control of the Open vSwitch inside the VMware
environment but through the API exposed by vSphere/NSX Manager.

For VMware DVS, the Neutron DHCP agent does not attaches to Open vSwitch inside
VMware environment, but attach to the Open vSwitch bridge called ``br-dvs`` on
the OpenStack side and replies to/receives DHCP packets through VLAN. Similar
to what the DHCP agent does, Neutron metadata agent attaches to ``br-dvs``
bridge and works through VLAN.

.. note::

   VMware NSX-DVS plugin does not support tenant networks, so all VMs should
   attach to Provider VLAN/Flat networks.

VMware NSX-V
~~~~~~~~~~~~

Preparation
-----------

You should have a working NSX-V environment, this part is out of scope
of Kolla.
For more information, please see `VMware NSX-V documentation <https://docs.vmware.com/en/VMware-NSX-for-vSphere/>`__.

.. note::

   In addition, it is important to modify the firewall rule of vSphere to make
   sure that VNC is accessible from outside VMware environment.

   On every VMware host, edit ``/etc/vmware/firewall/vnc.xml`` as below:

.. code-block:: xml

   <!-- FirewallRule for VNC Console -->
   <ConfigRoot>
   <service>
   <id>VNC</id>
   <rule id = '0000'>
   <direction>inbound</direction>
   <protocol>tcp</protocol>
   <porttype>dst</porttype>
   <port>
   <begin>5900</begin>
   <end>5999</end>
   </port>
   </rule>
   <rule id = '0001'>
   <direction>outbound</direction>
   <protocol>tcp</protocol>
   <porttype>dst</porttype>
   <port>
   <begin>0</begin>
   <end>65535</end>
   </port>
   </rule>
   <enabled>true</enabled>
   <required>false</required>
   </service>
   </ConfigRoot>

Then refresh the firewall config by:

.. code-block:: console

   # esxcli network firewall refresh

Verify that the firewall config is applied:

.. code-block:: console

   # esxcli network firewall ruleset list

Deployment
----------

Enable VMware nova-compute plugin and NSX-V neutron-server plugin in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   nova_compute_virt_type: "vmware"
   neutron_plugin_agent: "vmware_nsxv"

.. note::

   VMware NSX-V also supports Neutron FWaaS, LBaaS and VPNaaS services, you can enable
   them by setting these options in ``globals.yml``:

   * enable_neutron_vpnaas: "yes"
   * enable_neutron_lbaas: "yes"
   * enable_neutron_fwaas: "yes"

If you want to set VMware datastore as cinder backend, enable it in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_cinder: "yes"
   cinder_backend_vmwarevc_vmdk: "yes"
   vmware_datastore_name: "TestDatastore"

If you want to set VMware datastore as glance backend, enable it in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   glance_backend_vmware: "yes"
   vmware_vcenter_name: "TestDatacenter"
   vmware_datastore_name: "TestDatastore"

VMware options are required in ``/etc/kolla/globals.yml``, these options should
be configured correctly according to your NSX-V environment.

Options for ``nova-compute`` and ``ceilometer``:

.. code-block:: yaml

   vmware_vcenter_host_ip: "127.0.0.1"
   vmware_vcenter_host_username: "admin"
   vmware_vcenter_cluster_name: "cluster-1"
   vmware_vcenter_insecure: "True"
   vmware_vcenter_datastore_regex: ".*"

.. note::

   The VMware vCenter password has to be set in ``/etc/kolla/passwords.yml``.

   .. code-block:: yaml

      vmware_vcenter_host_password: "admin"

Options for Neutron NSX-V support:

.. code-block:: yaml

   vmware_nsxv_user: "nsx_manager_user"
   vmware_nsxv_manager_uri: "https://127.0.0.1"
   vmware_nsxv_cluster_moid: "TestCluster"
   vmware_nsxv_datacenter_moid: "TestDataCeter"
   vmware_nsxv_resource_pool_id: "TestRSGroup"
   vmware_nsxv_datastore_id: "TestDataStore"
   vmware_nsxv_external_network: "TestDVSPort-Ext"
   vmware_nsxv_vdn_scope_id: "TestVDNScope"
   vmware_nsxv_dvs_id: "TestDVS"
   vmware_nsxv_backup_edge_pool: "service:compact:1:2"
   vmware_nsxv_spoofguard_enabled: "false"
   vmware_nsxv_metadata_initializer: "false"
   vmware_nsxv_edge_ha: "false"

.. yaml

.. note::

   If you want to set secure connections to VMware, set ``vmware_vcenter_insecure``
   to false.
   Secure connections to vCenter requires a CA file, copy the vCenter CA file to
   ``/etc/kolla/config/vmware_ca``.

.. note::

   The VMware NSX-V password has to be set in ``/etc/kolla/passwords.yml``.

   .. code-block:: yaml

      vmware_nsxv_password: "nsx_manager_password"

Then you should start :command:`kolla-ansible` deployment normally as
KVM/QEMU deployment.


VMware NSX-DVS
~~~~~~~~~~~~~~

Preparation
-----------

Before deployment, you should have a working VMware vSphere environment.
Create a cluster and a vSphere Distributed Switch with all the host in the
cluster attached to it.

For more information, please see `Setting Up Networking with vSphere Distributed Switches <http://pubs.vmware.com/vsphere-51/index.jsp#com.vmware.vsphere.networking.doc/GUID-375B45C7-684C-4C51-BA3C-70E48DFABF04.html>`__.

Deployment
----------

Enable VMware nova-compute plugin and NSX-V neutron-server plugin in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   nova_compute_virt_type: "vmware"
   neutron_plugin_agent: "vmware_dvs"

If you want to set VMware datastore as Cinder backend, enable it in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_cinder: "yes"
   cinder_backend_vmwarevc_vmdk: "yes"
   vmware_datastore_name: "TestDatastore"

If you want to set VMware datastore as Glance backend, enable it in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   glance_backend_vmware: "yes"
   vmware_vcenter_name: "TestDatacenter"
   vmware_datastore_name: "TestDatastore"

VMware options are required in ``/etc/kolla/globals.yml``, these options should
be configured correctly according to the vSphere environment you installed
before. All option for nova, cinder, glance are the same as VMware-NSX, except
the following options.

Options for Neutron NSX-DVS support:

.. code-block:: yaml

   vmware_dvs_host_ip: "192.168.1.1"
   vmware_dvs_host_port: "443"
   vmware_dvs_host_username: "admin"
   vmware_dvs_dvs_name: "VDS-1"
   vmware_dvs_dhcp_override_mac: ""

.. note::

   The VMware NSX-DVS password has to be set in ``/etc/kolla/passwords.yml``.

   .. code-block:: yaml

      vmware_dvs_host_password: "password"

Then you should start :command:`kolla-ansible` deployment normally as
KVM/QEMU deployment.

For more information on OpenStack vSphere, see
`VMware vSphere
<https://docs.openstack.org/nova/latest/admin/configuration/hypervisor-vmware.html>`__,
`VMware-NSX package <https://github.com/openstack/vmware-nsx>`_.
