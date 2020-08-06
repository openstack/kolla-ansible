===
TLS
===

An additional endpoint configuration option is to enable or disable
TLS protection for the internal and/or external VIP. TLS allows a client to
authenticate the OpenStack service endpoint and allows for encryption of the
requests and responses.

The configuration variables that control TLS networking are:

- kolla_enable_tls_external
- kolla_external_fqdn_cert
- kolla_enable_tls_internal
- kolla_internal_fqdn_cert

.. note::

   If TLS is enabled only on the internal or the external network
   the kolla_internal_vip_address and kolla_external_vip_address must
   be different.

   If there is only a single network configured in your network topology
   (opposed to configuring seperate internal and external networks), TLS
   can be enabled using only the internal network configuration variables.

The default for TLS is disabled, to enable TLS networking:

.. code-block:: yaml

   kolla_enable_tls_external: "yes"
   kolla_external_fqdn_cert: "{{ kolla_certificates_dir }}/mycert.pem"

   and/or

   kolla_enable_tls_internal: "yes"
   kolla_internal_fqdn_cert: "{{ kolla_certificates_dir }}/mycert-internal.pem"


.. note::

   TLS authentication is based on certificates that have been
   signed by trusted Certificate Authorities. Examples of commercial
   CAs are Comodo, Symantec, GoDaddy, and GlobalSign. Letsencrypt.org
   is a CA that will provide trusted certificates at no charge. Many
   company's IT departments will provide certificates within that
   company's domain. If using a trusted CA is not possible for your
   situation, you can use `OpenSSL <https://www.openssl.org>`__
   to create your own company's domain or see the section below about
   kolla generated self-signed certificates.

Two certificate files are required to use TLS securely with authentication.
These two files will be provided by your Certificate Authority. These
two files are the server certificate with private key and the CA certificate
with any intermediate certificates. The server certificate needs to be
installed with the kolla deployment and is configured with the
``kolla_external_fqdn_cert`` or ``kolla_internal_fqdn_cert`` parameter.
If the server certificate provided is not already trusted by the client,
then the CA certificate file will need to be distributed to the client.

When using TLS to connect to a public endpoint, an OpenStack client will
have settings similar to this:

.. code-block:: shell

   export OS_PROJECT_DOMAIN_ID=default
   export OS_USER_DOMAIN_ID=default
   export OS_PROJECT_NAME=demo
   export OS_USERNAME=demo
   export OS_PASSWORD=demo-password
   export OS_AUTH_URL=https://mykolla.example.net:5000
   # os_cacert is optional for trusted certificates
   export OS_CACERT=/etc/pki/ca/mykolla-cacert.crt
   export OS_IDENTITY_API_VERSION=3

Self-Signed Certificates
~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

   Self-signed certificates should never be used in production.

It is not always practical to get a certificate signed by a well-known
trust CA, for example a development or internal test kolla deployment. In
these cases it can be useful to have a self-signed certificate to use.

For convenience, the ``kolla-ansible`` command will generate the necessary
certificate files based on the information in the ``globals.yml``
configuration file:

.. code-block:: console

   kolla-ansible certificates

The certificate file haproxy.pem will be generated and stored in the
``/etc/kolla/certificates/`` directory, and the CA cert will be in the
``/etc/kolla/certificates/ca/`` directory.

Adding CA Certificates to the Service Containers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To copy CA certificate files to the service containers

.. code-block:: yaml

   kolla_copy_ca_into_containers: "yes"

When ``kolla_copy_ca_into_containers`` is configured to "yes", the
CA certificate files in /etc/kolla/certificates/ca will be copied into
service containers to enable trust for those CA certificates. This is required
for any certificates that are either self-signed or signed by a private CA,
and are not already present in the service image trust store.

All certificate file names will have the "kolla-customca-" prefix prepended to
it when it is copied into the containers. For example, if a certificate file is
named "internal.crt", it will be named "kolla-customca-internal.crt" in the
containers.

For Debian and Ubuntu containers, the certificate files will be copied to
the ``/usr/local/share/ca-certificates/`` directory.

For Centos and Red Hat Linux containers, the certificate files will be copied
to the ``/etc/pki/ca-trust/source/anchors/`` directory.

In addition, the ``openstack_cacert`` should be configured with the path to
the cacert in the container. For example, if the self-signed certificate task
was used and the deployment is on ubuntu, the path would be:
"/etc/pki/ca-trust/source/anchors/kolla-customca-haproxy-internal.crt"
