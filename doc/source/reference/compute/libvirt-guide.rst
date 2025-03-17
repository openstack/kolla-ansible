====================================
Libvirt - Nova Virtualisation Driver
====================================

Overview
========

Libvirt is the most commonly used virtualisation driver in OpenStack. It uses
libvirt, backed by QEMU and when available, KVM. Libvirt is executed in the
``nova_libvirt`` container, or as a daemon running on the host.

Hardware Virtualisation
=======================

Two values are supported for ``nova_compute_virt_type`` with libvirt -
``kvm`` and ``qemu``, with ``kvm`` being the default.

For optimal performance, ``kvm`` is preferable, since many aspects of
virtualisation can be offloaded to hardware.  If it is not possible to enable
hardware virtualisation (e.g. Virtualisation Technology (VT) BIOS configuration
on Intel systems), ``qemu`` may be used to provide less performant
software-emulated virtualisation.

SASL Authentication
===================

The default configuration of Kolla Ansible is to run libvirt over TCP,
authenticated with SASL. This should not be considered as providing a secure,
encrypted channel, since the username/password SASL mechanisms available for
TCP are no longer considered cryptographically secure. However, it does at
least provide some authentication for the libvirt API. For a more secure
encrypted channel, use :ref:`libvirt TLS <libvirt-tls>`.

SASL is enabled according to the ``libvirt_enable_sasl`` flag, which defaults
to ``true``.

The username is configured via ``libvirt_sasl_authname``, and defaults to
``nova``. The password is configured via ``libvirt_sasl_password``, and is
generated with other passwords using ``kolla-mergepwd`` and ``kolla-genpwd``
and stored in ``passwords.yml``.

The list of enabled authentication mechanisms is configured via
``libvirt_sasl_mech_list``, and defaults to ``["SCRAM-SHA-256"]`` if libvirt
TLS is enabled, or ``["DIGEST-MD5"]`` otherwise.

Host vs containerised libvirt
=============================

By default, Kolla Ansible deploys libvirt in a ``nova_libvirt`` container. In
some cases it may be preferable to run libvirt as a daemon on the compute hosts
instead.

Kolla Ansible does not currently support deploying and configuring
libvirt as a host daemon. However, since the Yoga release, if a libvirt daemon
has already been set up, then Kolla Ansible may be configured to use it. This
may be achieved by setting ``enable_nova_libvirt_container`` to ``false``.

When the firewall driver is set to ``openvswitch``, libvirt will plug VMs
directly into the integration bridge, ``br-int``. To do this it uses the
``ovs-vsctl`` utility. The search path for this binary is controlled by the
``$PATH`` environment variable (as seen by the libvirt process). There are a
few options to ensure that this binary can be found:

* Set ``openvswitch_ovs_vsctl_wrapper_enabled`` to ``True``. This will install
  a wrapper script to the path: ``/usr/bin/ovs-vsctl`` that will execute
  ``ovs-vsctl`` in the context of the ``openvswitch_vswitchd`` container. This
  option is useful if you do not have openvswitch installed on the host. It
  also has the advantage that the ``ovs-vsctl`` utility will match the version
  of the server.

* Install openvswitch on the hypervisor. Kolla mounts ``/run/openvswitch`` from
  the host into the ``openvswitch_vswitchd`` container. This means that socket
  is in the location ``ovs-vsctl`` expects with its default options.

Migration from container to host
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``kolla-ansible nova-libvirt-cleanup`` command may be used to clean up the
``nova_libvirt`` container and related items on hosts, once it has
been disabled. This should be run after the compute service has been disabled,
and all active VMs have been migrated away from the host.

By default, the command will fail if there are any VMs running on the host. If
you are sure that it is safe to clean up the ``nova_libvirt`` container with
running VMs, setting ``nova_libvirt_cleanup_running_vms_fatal`` to ``false``
will allow the command to proceed.

The ``nova_libvirt`` container has several associated Docker volumes:
``libvirtd``, ``nova_libvirt_qemu`` and ``nova_libvirt_secrets``. By default,
these volumes are not cleaned up. If you are sure that the data in these
volumes can be safely removed, setting ``nova_libvirt_cleanup_remove_volumes``
to ``true`` will cause the Docker volumes to be removed.

A future extension could support migration of existing VMs, but this is
currently out of scope.

.. _libvirt-tls:

Libvirt TLS
===========

The default configuration of Kolla Ansible is to run libvirt over TCP, with
SASL authentication. As long as one takes steps to protect who can access
the network this works well. However, in a less trusted environment one may
want to use encryption when accessing the libvirt API. To do this we can enable
TLS for libvirt and make nova use it. Mutual TLS is configured, providing
authentication of clients via certificates. SASL authentication provides a
further level of security.

Using libvirt TLS
~~~~~~~~~~~~~~~~~

Libvirt TLS can be enabled in Kolla Ansible by setting the following option in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   libvirt_tls: "yes"

Creation of production-ready TLS certificates is currently out-of-scope for
Kolla Ansible.  You will need to either use an existing Internal CA or you will
need to generate your own offline CA. For the TLS communication to work
correctly you will have to supply Kolla Ansible the following pieces of
information:

* cacert.pem

  - This is the CA's public certificate that all of the client and server
    certificates are signed with. Libvirt and nova-compute will need this so
    they can verify that all the certificates being used were signed by the CA
    and should be trusted.

* serverkey.pem (not used when using a host libvirt daemon)

  - This is the private key for the server, and is no different than the
    private key of a TLS certificate. It should be carefully protected, just
    like the private key of a TLS certificate.

* servercert.pem (not used when using a host libvirt daemon)

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

* ``/etc/kolla/config/nova/nova-libvirt/<hostname>/``
* ``/etc/kolla/config/nova/nova-libvirt/``

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

Generating certificates for test and development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since the Yoga release, the ``kolla-ansible certificates`` command generates
certificates for libvirt TLS. A single key and certificate is used for all
hosts, with a Subject Alternative Name (SAN) entry for each compute host
hostname.
