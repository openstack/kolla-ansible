.. _ironic-guide:

================================
Ironic - Bare Metal provisioning
================================

Overview
~~~~~~~~
Ironic is the OpenStack service for handling bare metal, i.e., the physical
machines. It can work standalone as well as with other OpenStack services
(notably, Neutron and Nova).

Pre-deployment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Enable Ironic in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_ironic: "yes"

In the same file, define a network interface as the default NIC for dnsmasq and
define a network to be used for the Ironic cleaning network:

.. code-block:: yaml

   ironic_dnsmasq_interface: "eth1"
   ironic_cleaning_network: "public1"

Finally, define at least one DHCP range for Ironic inspection:

.. code-block:: yaml

   ironic_dnsmasq_dhcp_ranges:
     - range: "192.168.5.100,192.168.5.110"

Another example of a single range with a router (multiple routers
are possible by separating addresses with commas):

.. code-block:: yaml

   ironic_dnsmasq_dhcp_ranges:
     - range: "192.168.5.100,192.168.5.110"
       routers: "192.168.5.1"

Together with an router there can be provided the NTP (time source) server.
For example it can be the same address as default router for the range:

.. code-block:: yaml

   ironic_dnsmasq_dhcp_ranges:
     - range: "192.168.5.100,192.168.5.110"
       routers: "192.168.5.1"
       ntp_server: "192.168.5.1"

To support DHCP relay, it is also possible to define a netmask in the range.
It is advisable to also provide a router to allow the traffic to reach the
Ironic server.

.. code-block:: yaml

  ironic_dnsmasq_dhcp_ranges:
    - range: "192.168.5.100,192.168.5.110,255.255.255.0"
      routers: "192.168.5.1"

Multiple ranges are possible, they can be either for directly-connected
interfaces or relays (if with netmask):

.. code-block:: yaml

  ironic_dnsmasq_dhcp_ranges:
    - range: "192.168.5.100,192.168.5.110"
    - range: "192.168.6.100,192.168.6.110,255.255.255.0"
      routers: "192.168.6.1"

The default lease time for each range can be configured globally via
``ironic_dnsmasq_dhcp_default_lease_time`` variable or per range via
``lease_time`` parameter.

In the same file, specify the PXE bootloader file for Ironic inspection. The
file is relative to the ``/var/lib/ironic/tftpboot`` directory. The default is
``pxelinux.0``, and should be correct for x86 systems. Other platforms may
require a different value, for example aarch64 on Debian requires
``debian-installer/arm64/bootnetaa64.efi``.

.. code-block:: yaml

   ironic_dnsmasq_boot_file: pxelinux.0

Ironic inspection also requires a deploy kernel and ramdisk to be placed in
``/etc/kolla/config/ironic/``. The following example uses coreos which is
commonly used in Ironic deployments, though any compatible kernel/ramdisk may
be used:

.. code-block:: console

   $ curl https://tarballs.opendev.org/openstack/ironic-python-agent/dib/files/ipa-centos9-|KOLLA_BRANCH_NAME_DASHED|.kernel \
     -o /etc/kolla/config/ironic/ironic-agent.kernel

   $ curl https://tarballs.opendev.org/openstack/ironic-python-agent/dib/files/ipa-centos9-|KOLLA_BRANCH_NAME_DASHED|.initramfs \
     -o /etc/kolla/config/ironic/ironic-agent.initramfs

You may optionally pass extra kernel parameters to the inspection kernel using:

.. code-block:: yaml

   ironic_kernel_cmdline_extras: ['ipa-lldp-timeout=90.0', 'ipa-collect-lldp=1']

in ``/etc/kolla/globals.yml``.

PXE filter (optional)
~~~~~~~~~~~~~~~~~~~~~

To keep parity with the standalone inspector you can enable the experimental
PXE filter service:

.. code-block:: yaml

   enable_ironic_pxe_filter: "yes"

The PXE filter container runs alongside ``ironic-dnsmasq`` and cleans up stale
DHCP entries. It is especially useful when auto discovery is enabled and when
the dnsmasq DHCP range overlaps with a Neutron-served network. For the upstream
details see
https://docs.openstack.org/ironic/latest/admin/inspection/pxe_filter.html.

.. note::

   Upstream still classifies this PXE filter implementation as experimental.

Configure conductor's HTTP server port (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The port used for conductor's HTTP server is controlled via
``ironic_http_port`` in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

    ironic_http_port: "8089"

Revert to plain PXE (not recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Starting with Yoga, Ironic has changed the default PXE from plain PXE to iPXE.
Kolla Ansible follows this upstream decision by choosing iPXE as the default
for Ironic inspection but allows users to revert to the previous default of
plain PXE by setting the following in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   ironic_dnsmasq_serve_ipxe: "no"

To revert Ironic to previous default as well, set ``pxe`` as
``default_boot_interface`` in ``/etc/kolla/config/ironic.conf``:

.. code-block:: yaml

   [DEFAULT]
   default_boot_interface = pxe

Attach ironic to external keystone (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In :kolla-ansible-doc:`multi-regional <user/multi-regions.html>` deployment
keystone could be installed in one region (let's say region 1) and ironic -
in another region (let's say region 2). In this case we don't install keystone
together with ironic in region 2, but have to configure ironic to connect to
existing keystone in region 1. To deploy ironic in this way we have to set
variable ``enable_keystone`` to ``"no"``.

.. code-block:: yaml

    enable_keystone: "no"

It will prevent keystone from being installed in region 2.

To add keystone-related sections in ironic.conf, it is also needed to set
variable ``ironic_enable_keystone_integration`` to ``"yes"``

.. code-block:: yaml

    ironic_enable_keystone_integration: "yes"

Avoiding problems with high availability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

    This section assumes that you have not yet deployed the Nova Compute
    Ironic service. If you have already deployed multiple instances of the
    service and have one or more baremetal nodes registered, the following
    operations are non-trivial. You will likely have to use the `nova-manage`
    command (or pre-Caracal edit the DB) to ensure that all Ironic nodes
    are registered with a single Nova Compute Ironic instance. This is
    an advanced subject and is not covered here. Stop now if you don't
    know what you are doing.

Nova Compute Ironic HA is known to be unstable. Pending a better solution,
a workaround is to avoid the feature by running a single Nova Compute Ironic
instance. For example:

.. code-block:: diff

  - [nova-compute-ironic:children]
  - nova
  + [nova-compute-ironic]
  + controller1

If you choose to do this, it is helpful to pin the service host name
to a 'synthetic' constant. This means that if you need to re-deploy the
service to another host, the Ironic nodes will automatically use the new
service instance. Otherwise you will need to manually move active Ironic nodes
to the new service, with either the `nova-manage` CLI, or pre-Caracal, by
editing the Nova database.

The config option to pin the host name is `nova_compute_ironic_custom_host`
and must be set as a group or host var. Note that, unless you know what you
are doing, you must not change or set this option if you have already deployed
Ironic nodes.

This config option is also useful for Ironic Shards. Whilst these are not
explicitly supported by Kolla Ansible, some further information can be found
`here <https://specs.openstack.org/openstack/nova-specs/specs/2024.1/approved/ironic-shards.html>`__.

Note that Ironic HA is not affected, and continues to work as normal.

Deployment
~~~~~~~~~~
Run the deploy as usual:

.. code-block:: console

  $ kolla-ansible deploy


Post-deployment configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The :ironic-doc:`Ironic documentation <install/configure-glance-images>`
describes how to create the deploy kernel and ramdisk and register them with
Glance. In this example we're reusing the same images that were fetched for the
inspection:

.. code-block:: console

  openstack image create --disk-format aki --container-format aki --public \
    --file /etc/kolla/config/ironic/ironic-agent.kernel deploy-vmlinuz

  openstack image create --disk-format ari --container-format ari --public \
    --file /etc/kolla/config/ironic/ironic-agent.initramfs deploy-initrd

The :ironic-doc:`Ironic documentation <install/configure-nova-flavors>`
describes how to create Nova flavors for bare metal.  For example:

.. code-block:: console

  openstack flavor create my-baremetal-flavor \
    --ram 512 --disk 1 --vcpus 1 \
    --property resources:CUSTOM_BAREMETAL_RESOURCE_CLASS=1 \
    --property resources:VCPU=0 \
    --property resources:MEMORY_MB=0 \
    --property resources:DISK_GB=0

The :ironic-doc:`Ironic documentation <install/enrollment>` describes how to
enroll baremetal nodes and ports.  In the following example ensure to
substitute correct values for the kernel, ramdisk, and MAC address for your
baremetal node.

.. code-block:: console

  openstack baremetal node create --driver ipmi --name baremetal-node \
    --driver-info ipmi_port=6230 --driver-info ipmi_username=admin \
    --driver-info ipmi_password=password \
    --driver-info ipmi_address=192.168.5.1 \
    --resource-class baremetal-resource-class --property cpus=1 \
    --property memory_mb=512 --property local_gb=1 \
    --property cpu_arch=x86_64 \
    --driver-info deploy_kernel=15f3c95f-d778-43ad-8e3e-9357be09ca3d \
    --driver-info deploy_ramdisk=9b1e1ced-d84d-440a-b681-39c216f24121

  openstack baremetal port create 52:54:00:ff:15:55 \
    --node 57aa574a-5fea-4468-afcf-e2551d464412 \
    --physical-network physnet1

Make the baremetal node available to nova:

.. code-block:: console

  openstack baremetal node manage 57aa574a-5fea-4468-afcf-e2551d464412
  openstack baremetal node provide 57aa574a-5fea-4468-afcf-e2551d464412

It may take some time for the node to become available for scheduling in nova.
Use the following commands to wait for the resources to become available:

.. code-block:: console

  openstack hypervisor stats show
  openstack hypervisor show 57aa574a-5fea-4468-afcf-e2551d464412

Booting the baremetal
~~~~~~~~~~~~~~~~~~~~~
Assuming you have followed the examples above and created the demo resources
as shown in the :doc:`../../user/quickstart`, you can now use the following
example command to boot the baremetal instance:

.. code-block:: console

  openstack server create --image cirros --flavor my-baremetal-flavor \
    --key-name mykey --network public1 demo1

In other cases you will need to adapt the command to match your environment.

Notes
~~~~~

Debugging DHCP
--------------
The following `tcpdump` command can be useful when debugging why dhcp
requests may not be hitting various pieces of the process:

.. code-block:: console

  tcpdump -i <interface> port 67 or port 68 or port 69 -e -n

Configuring the Web Console
---------------------------
Configuration based off upstream :ironic-doc:`Node web console
<admin/console.html#node-web-console>`.

Serial speed must be the same as the serial configuration in the BIOS settings.
Default value: 115200bps, 8bit, non-parity.If you have different serial speed.

Set ironic_console_serial_speed in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   ironic_console_serial_speed: 9600n8

Deploying using virtual baremetal (vbmc + libvirt)
--------------------------------------------------
See https://brk3.github.io/post/kolla-ironic-libvirt/
