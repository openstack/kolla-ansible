.. _ironic-guide:

===============
Ironic in Kolla
===============

Overview
========
Currently Kolla can deploy the Ironic services:

- ironic-api
- ironic-conductor
- ironic-dnsmasq
- ironic-inspector

As well as a required PXE service, deployed as ironic-pxe.

Current status
==============
The Ironic implementation is "tech preview", so currently instances can only be
deployed on baremetal. Further work will be done to allow scheduling for both
virtualized and baremetal deployments.

Pre-deployment Configuration
============================

Enable Ironic role in ``/etc/kolla/globals.yml``:

.. code-block:: console

    enable_ironic: "yes"

Beside that an additional network type 'vlan,flat' has to be added to a list of
tenant network types:

.. code-block:: console

    neutron_tenant_network_types: "vxlan,vlan,flat"

Configuring Web Console
=======================
Configuration based off upstream web_console_documentation_.

Serial speed must be the same as the serial configuration in the BIOS settings.
Default value: 115200bps, 8bit, non-parity.If you have different serial speed.

Set ironic_console_serial_speed in ``/etc/kolla/globals.yml``:

::

    ironic_console_serial_speed: 9600n8

.. _web_console_documentation: https://docs.openstack.org/ironic/latest/admin/console.html#node-web-console

Post-deployment configuration
=============================
Configuration based off upstream documentation_.

Again, remember that enabling Ironic reconfigures nova compute (driver and
scheduler) as well as changes neutron network settings. Further neutron setup
is required as outlined below.

Create the flat network to launch the instances:
::

    neutron net-create --tenant-id $TENANT_ID sharednet1 --shared \
    --provider:network_type flat --provider:physical_network physnet1

    neutron subnet-create sharednet1 $NETWORK_CIDR --name $SUBNET_NAME \
    --ip-version=4 --gateway=$GATEWAY_IP --allocation-pool \
    start=$START_IP,end=$END_IP --enable-dhcp

And then the above ID is used to set cleaning_network in the neutron
section of ironic.conf.

.. _documentation: https://docs.openstack.org/ironic/latest/install/index.html
