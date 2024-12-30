==================================
Magnum - Container cluster service
==================================

Magnum is an OpenStack service that provides support for deployment and
management of container clusters such as Kubernetes. See the
:magnum-doc:`Magnum documentation </>` for information on using Magnum.

Configuration
=============

Enable Magnum, in ``globals.yml``:

.. code-block:: yaml

   enable_magnum: true

Optional: enable cluster user trust
-----------------------------------

This allows the cluster to communicate with OpenStack on behalf of the user
that created it, and is necessary for the auto-scaler and auto-healer to work.
Note that this is disabled by default since it exposes the cluster to
`CVE-2016-7404 <https://nvd.nist.gov/vuln/detail/CVE-2016-7404>`__. Ensure that
you understand the consequences before enabling this option. In
``globals.yml``:

.. code-block:: yaml

   enable_cluster_user_trust: true

Optional: private CA
--------------------

If using TLS with a private CA for OpenStack public APIs, the cluster will need
to add the CA certificate to its trust store in order to communicate with
OpenStack. The certificate must be available in the magnum conductor container.
It is copied to the cluster via user-data, so it is better to include only the
necessary certificates to avoid exceeding the max Nova API request body size
(this may be set via ``[oslo_middleware] max_request_body_size`` in
``nova.conf`` if necessary). In ``/etc/kolla/config/magnum.conf``:

.. code-block:: ini

   [drivers]
   openstack_ca_file = <path to CA file>

If using Kolla Ansible to :ref:`copy CA certificates into containers
<admin-tls-ca-in-containers>`, the certificates are located at
``/etc/pki/ca-trust/source/anchors/kolla-customca-*.crt``.

Deployment
==========

To deploy magnum and its dashboard in an existing OpenStack cluster:

.. code-block:: console

   kolla-ansible deploy -i <inventory> --tags common,horizon,magnum
