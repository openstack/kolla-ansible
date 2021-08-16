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

Libvirt
-------

Information on the libvirt-based drivers ``kvm`` and ``qemu`` can be found in
:doc:`libvirt-guide`.

VMware
------

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
Valid options are ``none``, ``novnc`` and ``spice``. Additionally,
serial console support can be enabled by setting
``enable_nova_serialconsole_proxy`` to ``yes``.

Cells
=====

Information on using Nova Cells V2 to scale out can be found in
:doc:`nova-cells-guide`.

Vendordata
==========

Nova supports passing deployer provided data to instances using a
concept known as Vendordata. If a Vendordata file is located in the
following path within the Kolla configuration, Kolla will
automatically use it when the Nova service is deployed or
reconfigured: ``/etc/kolla/config/nova/vendordata.json``.

Failure handling
================

Compute service registration
----------------------------

During deployment, Kolla Ansible waits for Nova compute services to register
themselves. By default, if a compute service does not register itself before
the timeout, that host will be marked as failed in the Ansible run. This
behaviour is useful at scale, where failures are more frequent.

Alternatively, to fail all hosts in a cell when any compute service fails
to register, set ``nova_compute_registration_fatal`` to ``true``.
