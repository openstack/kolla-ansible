======================
Nova - Compute Service
======================

Nova is a core service in OpenStack, and provides compute services. Typically
this is via Virtual Machines (VMs), but may also be via bare metal servers if
Nova is coupled with Ironic.

Nova is enabled by default, but may be disabled by setting ``enable_nova`` to
``no`` in ``globals.yml``.

Virtualisation Drivers
======================

The virtualisation driver may be selected via ``nova_compute_virt_type`` in
``globals.yml``. Supported options are ``qemu``, ``kvm``, and ``vmware``.
The default is ``kvm``.

HyperV
------

.. note::

   Hyper-V support has been deprecated and will be removed in the Victoria cycle.

Information on using Nova with HyperV can be found in :doc:`hyperv-guide`.

Libvirt
-------

Information on the libvirt-based drivers ``kvm`` and ``qemu`` can be found in
:doc:`libvirt-guide`.

VMware
------

.. note::

   VMware support has been deprecated and will be removed in the Victoria cycle.

Information on the VMware-based driver ``vmware`` can be found in
:doc:`vmware-guide`.

Bare Metal
----------

Information on using Nova with Ironic to deploy compute instances to bare metal
can be found in :doc:`../bare-metal/ironic-guide`.

Fake Driver
-----------

The fake driver can be used for testing Nova's scaling properties without
requiring access to a large amount of hardware resources. It is covered in
:doc:`nova-fake-driver`.

.. _nova-consoles:

Consoles
========

The console driver may be selected via ``nova_console`` in ``globals.yml``.
Valid options are ``none``, ``novnc``, ``spice``, or ``rdp``. Additionally,
serial console support can be enabled by setting
``enable_nova_serialconsole_proxy`` to ``yes``.

Cells
=====

Information on using Nova Cells V2 to scale out can be found in
:doc:`nova-cells-guide`.
