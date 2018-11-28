.. _ironic-guide:

================================
Ironic - Bare Metal provisioning
================================

Overview
~~~~~~~~
Ironic works well in Kolla, though it is not currently tested as part of Kolla
CI, so may be subject to instability.

Pre-deployment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Enable Ironic in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_ironic: "yes"

In the same file, define a network interface as the default NIC for dnsmasq,
a range of IP addresses that will be available for use by Ironic inspector,
as well as a network to be used for the Ironic cleaning network:

.. code-block:: yaml

   ironic_dnsmasq_interface: "eth1"
   ironic_dnsmasq_dhcp_range: "192.168.5.100,192.168.5.110"
   ironic_cleaning_network: "public1"

In the same file, optionally a default gateway to be used for the Ironic
Inspector inspection network:

.. code-block:: yaml

   ironic_dnsmasq_default_gateway: 192.168.5.1

In the same file, specify the PXE bootloader file for Ironic Inspector. The
file is relative to the ``/tftpboot`` directory. The default is ``pxelinux.0``,
and should be correct for x86 systems. Other platforms may require a different
value, for example aarch64 on Debian requires
``debian-installer/arm64/bootnetaa64.efi``.

.. code-block:: yaml

   ironic_dnsmasq_boot_file: pxelinux.0

Ironic inspector also requires a deploy kernel and ramdisk to be placed in
``/etc/kolla/config/ironic/``. The following example uses coreos which is
commonly used in Ironic deployments, though any compatible kernel/ramdisk may
be used:

.. code-block:: console

   $ curl https://tarballs.openstack.org/ironic-python-agent/coreos/files/coreos_production_pxe.vmlinuz \
     -o /etc/kolla/config/ironic/ironic-agent.kernel

   $ curl https://tarballs.openstack.org/ironic-python-agent/coreos/files/coreos_production_pxe_image-oem.cpio.gz \
     -o /etc/kolla/config/ironic/ironic-agent.initramfs

You may optionally pass extra kernel parameters to the inspection kernel using:

.. code-block:: yaml

   ironic_inspector_kernel_cmdline_extras: ['ipa-lldp-timeout=90.0', 'ipa-collect-lldp=1']

in ``/etc/kolla/globals.yml``.

Enable iPXE booting (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can optionally enable booting via iPXE by setting ``enable_ironic_ipxe`` to
true in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

    enable_ironic_ipxe: "yes"

This will enable deployment of a docker container, called ironic_ipxe, running
the web server which iPXE uses to obtain it's boot images.

The port used for the iPXE webserver is controlled via ``ironic_ipxe_port`` in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

    ironic_ipxe_port: "8089"

The following changes will occur if iPXE booting is enabled:

- Ironic will be configured with the ``ipxe_enabled`` configuration option set
  to true
- The inspection ramdisk and kernel will be loaded via iPXE
- The DHCP servers will be configured to chainload iPXE from an existing PXE
  environment. You may also boot directly to iPXE by some other means e.g by
  burning it to the option rom of your ethernet card.

Deployment
~~~~~~~~~~
Run the deploy as usual:

.. code-block:: console

  $ kolla-ansible deploy


Post-deployment configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A script named `init-runonce` is supplied as part of kolla-ansible to
initialise the cloud with some defaults (only to be used for demo purposes):

.. code-block:: console

  tools/init-runonce

Add the deploy kernel and ramdisk to Glance. Here we're reusing the same images
that were fetched for the Inspector:

.. code-block:: console

  openstack image create --disk-format aki --container-format aki --public \
    --file /etc/kolla/config/ironic/ironic-agent.kernel deploy-vmlinuz

  openstack image create --disk-format ari --container-format ari --public \
    --file /etc/kolla/config/ironic/ironic-agent.initramfs deploy-initrd

Create a baremetal flavor:

.. code-block:: console

  openstack flavor create --ram 512 --disk 1 --vcpus 1 my-baremetal-flavor
  openstack flavor set my-baremetal-flavor --property \
    resources:CUSTOM_BAREMETAL_RESOURCE_CLASS=1

Create the baremetal node and associate a port. (Ensure to substitute correct
values for the kernel, ramdisk, and MAC address for your baremetal node)

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

  openstack baremetal port create 52:54:00:ff:15:55 --node 57aa574a-5fea-4468-afcf-e2551d464412

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
You can now use the following sample command to boot the baremetal instance:

.. code-block:: console

  openstack server create --image cirros --flavor my-baremetal-flavor \
    --key-name mykey --network public1 demo1

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
Configuration based off upstream `Node web console
<https://docs.openstack.org/ironic/latest/admin/console.html#node-web-console>`__.

Serial speed must be the same as the serial configuration in the BIOS settings.
Default value: 115200bps, 8bit, non-parity.If you have different serial speed.

Set ironic_console_serial_speed in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   ironic_console_serial_speed: 9600n8

Deploying using virtual baremetal (vbmc + libvirt)
--------------------------------------------------
See https://brk3.github.io/post/kolla-ironic-libvirt/
