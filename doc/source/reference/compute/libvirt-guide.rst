.. libvirt-tls-guide:

====================================
Libvirt - Nova Virtualisation Driver
====================================

Overview
========

Libvirt is the most commonly used virtualisation driver in OpenStack. It uses
libvirt, backed by QEMU and when available, KVM. Libvirt is executed in the
``nova_libvirt`` container.

Hardware Virtualisation
=======================

Two values are supported for ``nova_compute_virt_type`` with libvirt -
``kvm`` and ``qemu``, with ``kvm`` being the default.

For optimal performance, ``kvm`` is preferable, since many aspects of
virtualisation can be offloaded to hardware.  If it is not possible to enable
hardware virtualisation (e.g. Virtualisation Technology (VT) BIOS configuration
on Intel systems), ``qemu`` may be used to provide less performant
software-emulated virtualisation.

Libvirt TLS
===========

The default configuration of Kolla Ansible is to run libvirt over TCP, with
authentication disabled. As long as one takes steps to protect who can access
the port this works well. However, in the case where you want live-migration to
be allowed across hypervisors one may want to either add some level of
authentication to the connections or make sure VM data is passed between
hypervisors in a secure manner. To do this we can enable TLS for libvirt and
make nova use it.

Using libvirt TLS
~~~~~~~~~~~~~~~~~

Libvirt TLS can be enabled in Kolla Ansible by setting the following option in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   libvirt_tls: "yes"

Creation of the TLS certificates is currently out-of-scope for Kolla Ansible.
You will need to either use an existing Internal CA or you will need to
generate your own offline CA. For the TLS communication to work correctly you
will have to supply Kolla Ansible the following pieces of information:

* cacert.pem

  - This is the CA's public certificate that all of the client and server
    certificates are signed with. Libvirt and nova-compute will need this so
    they can verify that all the certificates being used were signed by the CA
    and should be trusted.

* serverkey.pem

  - This is the private key for the server, and is no different than the
    private key of a TLS certificate. It should be carefully protected, just
    like the private key of a TLS certificate.

* servercert.pem

  - This is the public certificate for the server. Libvirt will present this
    certificate to any connection made to the TLS port. This is no different
    than the public certificate part of a standard TLS certificate/key bundle.

* clientkey.pem

  - This is the client private key, which nova-compute/libvirt will use
    when it is connecting to libvirt. Think of this as an SSH private key
    and protect it in a similar manner.

* clientcert.pem

  - This is the client certificate that nova-compute/libvirt will present when
    it is connecting to libvirt. Think of this as the public side of an SSH
    key.

Kolla Ansible will search for these files for each compute node in the
following locations and order on the host where Kolla Ansible is executed:

- ``/etc/kolla/config/nova/nova-libvirt/<hostname>/``
- ``/etc/kolla/config/nova/nova-libvirt/``

In most cases you will want to have a unique set of server and client
certificates and keys per hypervisor and with a common CA certificate. In this
case you would place each of the server/client certificate and key PEM files
under ``/etc/kolla/config/nova/nova-libvirt/<hostname>/`` and the CA
certificate under ``/etc/kolla/config/nova/nova-libvirt/``.

However, it is possible to make use of wildcard server certificate and a single
client certificate that is shared by all servers. This will allow you to
generate a single client certificate and a single server certificate that is
shared across every hypervisor. In this case you would store everything under
``/etc/kolla/config/nova/nova-libvirt/``.

Externally managed certificates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One more option for deployers who already have automation to get TLS certs onto
servers is to disable certificate management under ``/etc/kolla/globals.yaml``:

.. code-block:: yaml

   libvirt_tls_manage_certs: "no"

With this option disabled Kolla Ansible will simply assume that certificates
and keys are already installed in their correct locations. Deployers will be
responsible for making sure that the TLS certificates/keys get placed in to the
correct container configuration directories on the servers so that they can get
copied into the nova-compute and nova-libvirt containers. With this option
disabled you will also be responsible for restarting the nova-compute and
nova-libvirt containers when the certs are updated, as kolla-ansible will not
be able to tell when the files have changed.
