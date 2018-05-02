.. _ironic-guide:

===============
Ironic in Kolla
===============

Overview
~~~~~~~~
Ironic works well in Kolla, though it is not currently tested as part of Kolla
CI, so may be subject to instability.

Pre-deployment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Enable Ironic in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_ironic: "yes"

.. end

In the same file, define a range of IP addresses that will be available for use
by Ironic inspector, as well as a network to be used for the Ironic cleaning
network:

.. code-block:: yaml

   ironic_dnsmasq_dhcp_range: "192.168.5.100,192.168.5.110"
   ironic_cleaning_network: "public1"

.. end

Ironic inspector also requires a deploy kernel and ramdisk to be placed in
``/etc/kolla/config/ironic/``. The following example uses coreos which is
commonly used in Ironic deployments, though any compatible kernel/ramdisk may
be used:

.. code-block:: console

   $ curl https://tarballs.openstack.org/ironic-python-agent/coreos/files/coreos_production_pxe.vmlinuz \
     -o /etc/kolla/config/ironic/ironic-agent.kernel

   $ curl https://tarballs.openstack.org/ironic-python-agent/coreos/files/coreos_production_pxe_image-oem.cpio.gz \
     -o /etc/kolla/config/ironic/ironic-agent.initramfs

.. end

Deployment
~~~~~~~~~~
Run the deploy as usual:

.. code-block:: console

  $ kolla-ansible deploy

.. end


Post-deployment configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A script named `init-runonce` is supplied as part of kolla-ansible to
initialise the cloud with some defaults (only to be used for demo purposes):

.. code-block:: console

  tools/init-runonce

.. end

Add the deploy kernel and ramdisk to Glance. Here we're reusing the same images
that were fetched for the Inspector:

.. code-block:: console

  openstack image create --disk-format aki --container-format aki --public \
    --file /etc/kolla/config/ironic/ironic-agent.kernel deploy-vmlinuz

  openstack image create --disk-format ari --container-format ari --public \
    --file /etc/kolla/config/ironic/ironic-agent.initramfs deploy-initrd

.. end

Create a baremetal flavor:

.. code-block:: console

  openstack flavor create --ram 512 --disk 1 --vcpus 1 my-baremetal-flavor
  openstack flavor set my-baremetal-flavor --property \
    resources:CUSTOM_BAREMETAL_RESOURCE_CLASS=1

.. end

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

.. end

Make the baremetal node available to nova:

.. code-block:: console

  openstack baremetal node manage 57aa574a-5fea-4468-afcf-e2551d464412
  openstack baremetal node provide 57aa574a-5fea-4468-afcf-e2551d464412

.. end

It may take some time for the node to become available for scheduling in nova.
Use the following commands to wait for the resources to become available:

.. code-block:: console

  openstack hypervisor stats show
  openstack hypervisor show 57aa574a-5fea-4468-afcf-e2551d464412

.. end

Booting the baremetal
~~~~~~~~~~~~~~~~~~~~~
You can now use the following sample command to boot the baremetal instance:

.. code-block:: console

  openstack server create --image cirros --flavor my-baremetal-flavor \
    --key-name mykey --network public1 demo1

.. end

Notes
~~~~~

Debugging DHCP
--------------
The following `tcpdump` command can be useful when debugging why dhcp
requests may not be hitting various pieces of the process:

.. code-block:: console

  tcpdump -i <interface> port 67 or port 68 or port 69 -e -n

.. end

Configuring the Web Console
---------------------------
Configuration based off upstream `Node web console
<https://docs.openstack.org/ironic/latest/admin/console.html#node-web-console>`__.

Serial speed must be the same as the serial configuration in the BIOS settings.
Default value: 115200bps, 8bit, non-parity.If you have different serial speed.

Set ironic_console_serial_speed in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   ironic_console_serial_speed: 9600n8

.. end

Deploying using virtual baremetal (vbmc + libvirt)
--------------------------------------------------
See https://brk3.github.io/post/kolla-ironic-libvirt/
