.. _masakari-guide:

=============================================
Masakari - Virtual Machines High Availability
=============================================

Overview
~~~~~~~~

Masakari provides Instances High Availability Service for OpenStack clouds by
automatically recovering failed Instances. Currently, Masakari can recover
KVM-based Virtual Machine(VM)s from failure events such as VM process down,
provisioning process down, and nova-compute host failure. Masakari also
provides an API service to manage and control the automated rescue mechanism.

Kolla deploys Masakari API, Masakari Engine and Masakari Monitor containers
which are the main Masakari components only if ``enable_masakari`` is set in
``/etc/kolla/globals.yml``. By default, both the Masakari Host Monitor and
Masakari Instance Monitor containers are enabled. The deployment of each type
of monitors can be controlled individually via
``enable_masakari_instancemonitor`` and ``enable_masakari_hostmonitor``.
