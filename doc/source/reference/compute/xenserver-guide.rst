.. _XenServer-guide:

=========
XenServer
=========

Overview
========

Kolla can deploy the OpenStack services on XenServer hosts by choosing
``xenapi`` as the compute virt driver.

In XenServer, there is a privileged domain which is known as dom0;
and it can run a number of un-privileged domains which are known as
domUs or VMs.

Most OpenStack services (e.g. Keystone, Glance, Horizon) can run either
in the XenServer VMs or in separate baremetal hosts, but some services
(which make direct use of the hypervisor) must run in the XenServer VMs.
These services will interact with the XenServer host via XenAPI to perform
privileged operations. See the following list for such kind of services:

* ``nova-compute``

* ``neutron-openvswitch-agent-xenapi``

* ``ceilometer-compute``


.. note::

   At the moment, only CentOS 7.x has been tested.

Preparation for compute node on XenServer hosts
===============================================

We need some bootstrap tasks particularly for XenAPI compute nodes. The
tasks are implemented in the package of ``python-os-xenapi`` and exposed
to kolla-ansible via a single command - ``xenapi_bootstrap``. This package
is contained in the ``RDO CloudSIG repository`` [`RDO repos`_] and will be
installed on compute nodes at nova deployment. So we need ensure this
repository is reachable from the compute nodes or cache the repository
locally.

Create a compute VM on each XenServer host which will be used to boot
instances on. The VM must meet the common requirements declared by
kolla-ansible for KVM/QEMU deployment.

Additionally you should install PV driver in the VM [`XenServer documents`_];
and create the HIMN(Host Internal Management Network) for each compute VM
by following these steps:

1. In XenCenter, from the menu choose "View ->  Hidden Objects";

2. You will see HIMN in the host's 'Networking' page;

3. Create an interface on HIMN for the compute VM.

The remaining instructions are just the same as the preparations for
KVM/QEMU deployment.

Deployment
----------

Enable the virt type ``xenapi`` and configure connection options in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

    nova_compute_virt_type: "xenapi"
    xenserver_username: "root"
    xenserver_connect_protocol: "https"

.. note::

    When using ``https`` as the connection protocol, please refer XenServer
    user document to setup the signed SSL certificates to allow the secure
    communications between dom0 and domU. Otherwise, please use ``http`` for
    self-signed certificates.

You also need set the password for xenserver_username in
``/etc/kolla/passwords.yml``:

.. code-block:: yaml

    xenserver_password: "root_password"

Then you can start kolla-ansible deployment just following the general
deployment instructions [`Quick Start`_].

References
==========

For more information on XenAPI OpenStack, see:

XenAPI OpenStack: https://docs.openstack.org/nova/latest/admin/configuration/hypervisor-xen-api.html

.. _RDO repos: https://www.rdoproject.org/what/repos/

.. _XenServer documents: https://docs.citrix.com/en-us/xenserver/current-release.html

.. _Quick Start: https://docs.openstack.org/kolla-ansible/latest/user/quickstart.html
