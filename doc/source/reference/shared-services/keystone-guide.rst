.. _keystone-guide:

===========================
Keystone - Identity service
===========================

Fernet Tokens
-------------

Fernet tokens require the use of keys that must be synchronised between
Keystone servers. Kolla Ansible deploys two containers to handle this -
``keystone_fernet`` runs cron jobs to rotate keys via rsync when necessary.
``keystone_ssh`` is an SSH server that provides the transport for rsync. In a
multi-host control plane, these rotations are performed by the hosts in a
round-robin manner.

The following variables may be used to configure the token expiry and key
rotation.

``fernet_token_expiry``
    Keystone fernet token expiry in seconds. Default is 86400, which is 1 day.
``fernet_token_allow_expired_window``
    Keystone window to allow expired fernet tokens. Default is 172800, which is
    2 days.
``fernet_key_rotation_interval``
    Keystone fernet key rotation interval in seconds. Default is sum of token
    expiry and allow expired window, which is 3 days.

The default rotation interval is set up to ensure that the minimum number of
keys may be active at any time. This is one primary key, one secondary key and
a buffer key - three in total. If the rotation interval is set lower than the
sum of the token expiry and token allow expired window, more active keys will
be configured in Keystone as necessary.

Further information on Fernet tokens is available in the
:keystone-doc:`Keystone documentation <admin/fernet-token-faq.html>`.

Federated identity
------------------

Keystone allows users to be authenticated via identity federation. This means
integrating OpenStack Keystone with an identity provider. The use of identity
federation allows users to access OpenStack services without the necessity of
an account in the OpenStack environment per se. The authentication is then
off-loaded to the identity provider of the federation.

To enable identity federation, you will need to execute a set of configurations
in multiple OpenStack systems. Therefore, it is easier to use Kolla Ansible
to execute this process for operators.

For upstream documentations, please see
:keystone-doc:`Configuring Keystone for Federation
<admin/federation/configure_federation.html>`

Supported protocols
~~~~~~~~~~~~~~~~~~~

OpenStack supports both OpenID Connect and SAML protocols for federated
identity, but for now, kolla Ansible supports only OpenID Connect.
Therefore, if you desire to use SAML in your environment, you will need
to set it up manually or extend Kolla Ansible to also support it.

.. _setup-oidc-kolla-ansible:

Setting up OpenID Connect via Kolla Ansible
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, you will need to register the OpenStack (Keystone) in your Identity
provider as a Service Provider.

After registering Keystone, you will need to add the Identity Provider
configurations in your kolla-ansible globals configuration as the example
below:

.. code-block:: yaml

    keystone_identity_providers:
      - name: "myidp1"
        openstack_domain: "my-domain"
        protocol: "openid"
        identifier: "https://accounts.google.com"
        public_name: "Authenticate via myidp1"
        attribute_mapping: "mappingId1"
        metadata_folder: "path/to/metadata/folder"
        certificate_file: "path/to/certificate/file.pem"

    keystone_identity_mappings:
      - name: "mappingId1"
        file: "/full/qualified/path/to/mapping/json/file/to/mappingId1"

In some cases it's necessary to add JWKS (JSON Web Key Set) uri.
It is required for auth-openidc endpoint - which is
used by OpenStack command line client. Example config shown below:

.. code-block:: yaml

    keystone_federation_oidc_jwks_uri: "https://<AUTH PROVIDER>/<ID>/discovery/v2.0/keys"

Some identity providers need additional mod_auth_openidc config.
Example for Keycloak shown below:

.. code-block:: yaml

    keystone_federation_oidc_additional_options:
      OIDCTokenBindingPolicy: disabled

When using OIDC, operators can also use the following variable
to customize the delay to retry authenticating in the IdP if the
authentication has timeout:

``keystone_federation_oidc_error_page_retry_login_delay_milliseconds``
    Default is 5000 milliseconds (5 seconds).

It is also possible to override the ``OIDCHTMLErrorTemplate``,
the custom error template page via:

.. code-block:: yaml

  {{ node_custom_config }}/keystone/federation/modoidc-error-page.html

Identity providers configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

name
****

The internal name of the Identity provider in OpenStack.

openstack_domain
****************

The OpenStack domain that the Identity Provider belongs.

protocol
********

The federated protocol used by the IdP; e.g. openid or saml. We support only
OpenID connect right now.

identifier
**********

The Identity provider URL; e.g. https://accounts.google.com .

public_name
***********

The Identity provider public name that will be shown for users in the Horizon
login page.

attribute_mapping
*****************

The attribute mapping to be used for the Identity Provider. This mapping is
expected to already exist in OpenStack or be configured in the
`keystone_identity_mappings` property.

metadata_folder
***************

Path to the folder containing all of the identity provider metadata as JSON
files.

The metadata folder must have all your Identity Providers configurations,
the name of the files will be the name (with path) of the Issuer configuration.
Such as:

.. code-block::

    - <IDP metadata directory>
      - keycloak.example.org%2Fauth%2Frealms%2Fidp.client
      |
      - keycloak.example.org%2Fauth%2Frealms%2Fidp.conf
      |
      - keycloak.example.org%2Fauth%2Frealms%2Fidp.provider

.. note::

  The name of the file must be URL-encoded if needed. For example, if you have
  an Issuer with ``/`` in the URL, then you need to escape it to ``%2F`` by
  applying a URL escape in the file name.

The content of these files must be a JSON

``client``:

The ``.client`` file handles the Service Provider credentials in the Issuer.

During the first step, when you registered the OpenStack as a
Service Provider in the Identity Provider, you submitted a `cliend_id` and
generated a `client_secret`, so these are the values you must use in this
JSON file.

.. code-block:: json

    {
      "client_id":"<openid_client_id>",
      "client_secret":"<openid_client_secret>"
    }

``conf``:

This file will be a JSON that overrides some of the OpenID Connect options. The
options that can be overridden are listed in the
`OpenID Connect Apache2 plugin documentation`_.
.. _`OpenID Connect Apache2 plugin documentation`: https://github.com/zmartzone/mod_auth_openidc/wiki/Multiple-Providers#opclient-configuration

If you do not want to override the config values, you can leave this file as
an empty JSON file such as ``{}``.

``provider``:

This file will contain all specifications about the IdentityProvider. To
simplify, you can just use the JSON returned in the ``.well-known``
Identity provider's endpoint:

.. code-block:: json

  {
    "issuer": "https://accounts.google.com",
    "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_endpoint": "https://oauth2.googleapis.com/token",
    "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
    "revocation_endpoint": "https://oauth2.googleapis.com/revoke",
    "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
    "response_types_supported": [
     "code",
     "token",
     "id_token",
     "code token",
     "code id_token",
     "token id_token",
     "code token id_token",
     "none"
    ],
    "subject_types_supported": [
     "public"
    ],
    "id_token_signing_alg_values_supported": [
     "RS256"
    ],
    "scopes_supported": [
     "openid",
     "email",
     "profile"
    ],
    "token_endpoint_auth_methods_supported": [
     "client_secret_post",
     "client_secret_basic"
    ],
    "claims_supported": [
     "aud",
     "email",
     "email_verified",
     "exp",
     "family_name",
     "given_name",
     "iat",
     "iss",
     "locale",
     "name",
     "picture",
     "sub"
    ],
    "code_challenge_methods_supported": [
     "plain",
     "S256"
    ]
  }

certificate_file
****************

Optional path to the Identity Provider certificate file.  If included,
the file must be named as 'certificate-key-id.pem'. E.g.:

.. code-block::

    - fb8ca5b7d8d9a5c6c6788071e866c6c40f3fc1f9.pem

You can find the key-id in the Identity provider
`.well-known/openid-configuration` `jwks_uri` like in
`https://www.googleapis.com/oauth2/v3/certs` :

.. code-block:: json

    {
      "keys": [
        {
          "e": "AQAB",
          "use": "sig",
          "n": "zK8PHf_6V3G5rU-viUOL1HvAYn7q--dxMoU...",
          "kty": "RSA",
          "kid": "fb8ca5b7d8d9a5c6c6788071e866c6c40f3fc1f9",
          "alg": "RS256"
        }
      ]
    }

.. note::

    The public key is different from the certificate, the file in this
    configuration must be the Identity provider's certificate and not the
    Identity provider's public key.
