.. _setup-identity-provider:

============================
Test Identity Provider setup
============================

This guide shows how to create an Identity Provider that handles the OpenID
Connect protocol to authenticate users when
:keystone-doc:`using Federation with OpenStack
</admin/federation/configure_federation.html>` (these configurations must not
be used in a production environment).

Keycloak
========

Keycloak is a Java application that implements an Identity Provider handling
both OpenID Connect and SAML protocols.

To setup a Keycloak instance for testing is pretty simple with Docker.

Creating the Docker Keycloak instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the docker command:

.. code-block:: console

    docker run -p 8080:8080 -p 8443:8443 -e KEYCLOAK_USER=admin -e KEYCLOAK_PASSWORD=admin quay.io/keycloak/keycloak:latest

This will create a Keycloak instance that has the admin credentials as
admin/admin and is listening on port 8080.

After creating the instance, you will need to log in to the Keycloak as
administrator and setup the first Identity Provider.

Creating an Identity Provider with Keycloak
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following guide assumes that the steps are executed from the same machine
(localhost), but you can change the hostname if you want to run it from
elsewhere.

In this guide, we will use the 'new_realm' as the realm name in Keycloak, so,
if you want to use any other realm name, you must to change 'new_realm' in the
URIs used in the guide and replace the 'new_realm' with the realm name that you
are using.

* Access the admin console on http://localhost:8080/auth/ in the Administration Console option.
* Authenticate using the credentials defined in the creation step.
* Create a new realm in the http://localhost:8080/auth/admin/master/console/#/create/realm page.
* After creating a realm, you will need to create a client to be used by Keystone; to do it, just access http://localhost:8080/auth/admin/master/console/#/create/client/new_realm.
* To create a client, you will need to set the client_id (just choose anyone),
  the protocol (must be openid-connect) and the Root Url (you can leave it
  blank)
* After creating the client, you will need to update some client's attributes
  like:

  - Enable the Implicit flow (this one allows you to use the OpenStack CLI with
    oidcv3 plugin)
  - Set Access Type to confidential
  - Add the Horizon and Keystone URIs to the Valid Redirect URIs. Keystone should be within the '/redirect_uri' path, for example: https://horizon.com/ and https://keystone.com/redirect_uri
  - Save the changes
  - Access the client's Mappers tab to add the user's attributes that will be
    shared with the client (Keystone):

    - In this guide, we will need the following attribute mappers in Keycloak:

      ==================================== ==============
      name/user attribute/token claim name mapper type
      ==================================== ==============
      openstack-user-domain                user attribute
      openstack-default-project            user attribute
      ==================================== ==============

* After creating the client, you will need to create a user in that realm to
  log in OpenStack via identity federation
* To create a user, access http://localhost:8080/auth/admin/master/console/#/create/user/new_realm and fill the form with the user's data
* After creating the user, you can access the tab "Credentials" to set the
  user's password
* Then, in the tab "Attributes", you must set the authorization attributes to
  be used by Keystone, these attributes are defined in the :ref:`attribute
  mapping <attribute_mapping>` in Keystone

After you create the Identity provider, you will need to get some data from the
Identity Provider to configure in Kolla-Ansible

Configuring Kolla Ansible to use the Identity Provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section is about how one can get the data needed in
:ref:`Setup OIDC via Kolla Ansible <setup-oidc-kolla-ansible>`.

* name: The realm name, in this case it will be "new_realm"
* identifier: http://localhost:8080/auth/realms/new_realm/ (again, the "new_realm" is the name of the realm)
* certificate_file: This one can be downloaded from http://localhost:8080/auth/admin/master/console/#/realms/new_realm/keys
* metadata_folder:

  - localhost%3A8080%2Fauth%2Frealms%2Fnew_realm.client:

    - client_id: Access http://localhost:8080/auth/admin/master/console/#/realms/new_realm/clients , and access the client you created for Keystone, copy the Client ID displayed in the page
    - client_secret: In the same page you got the client_id, access the tab
      "Credentials" and copy the secret value
  - localhost%3A8080%2Fauth%2Frealms%2Fnew_realm.provider: Copy the json from http://localhost:8080/auth/realms/new_realm/.well-known/openid-configuration (the "new_realm" is the realm name)
  - localhost%3A8080%2Fauth%2Frealms%2Fnew_realm.conf: You can leave this file
    as an empty json "{}"


After you finished the configuration of the Identity Provider, your main
configuration should look something like the following:

.. code-block::

    keystone_identity_providers:
      - name: "new_realm"
        openstack_domain: "new_domain"
        protocol: "openid"
        identifier: "http://localhost:8080/auth/realms/new_realm"
        public_name: "Authenticate via new_realm"
        attribute_mapping: "attribute_mapping_keycloak_new_realm"
        metadata_folder: "/root/inDev/meta-idp"
        certificate_file: "/root/inDev/certs/LRVweuT51StjMdsna59jKfB3xw0r8Iz1d1J1HeAbmlw.pem"
    keystone_identity_mappings:
      - name: "attribute_mapping_keycloak_new_realm"
        file: "/root/inDev/attr_map/attribute_mapping.json"

Then, after deploying OpenStack, you should be able to log in Horizon
using the "Authenticate using" -> "Authenticate via new_realm", and writing
"new_realm.com" in the "E-mail or domain name" field. After that, you will be
redirected to a new page to choose the Identity Provider in Keystone. Just click in the link
"localhost:8080/auth/realms/new_realm"; this will redirect you to Keycloak (idP) where
you will need to log in with the user that you created. If the user's
attributes in Keycloak are ok, the user will be created in OpenStack and you will
be able to log in Horizon.

.. _attribute_mapping:

Attribute mapping
~~~~~~~~~~~~~~~~~
This section shows how to create the attribute mapping to map an Identity
Provider user to a Keystone user (ephemeral).

The 'OIDC-' prefix in the remote types is defined in the 'OIDCClaimPrefix'
configuration in the wsgi-keystone.conf file; this prefix must be in the
attribute mapping as the mod-oidc-wsgi is adding the prefix in the user's
attributes before sending it to Keystone. The attribute 'openstack-user-domain'
will define the user's domain in OpenStack and the attribute
'openstack-default-project' will define the user's project in the OpenStack
(the user will be assigned with the role 'member' in the project)

.. code-block:: json

    [
        {
            "local": [
                {
                    "user": {
                        "name": "{0}",
                        "email": "{1}",
                        "domain": {
                            "name": "{2}"
                        }
                    },
                    "domain": {
                            "name": "{2}"
                        },
                    "projects": [
                        {
                            "name": "{3}",
                            "roles": [
                                {
                                    "name": "member"
                                }
                            ]
                        }
                    ]
                }
            ],
            "remote": [
                {
                    "type": "OIDC-preferred_username"
                },
                {
                    "type": "OIDC-email"
                },
                {
                    "type": "OIDC-openstack-user-domain"
                },
                {
                    "type": "OIDC-openstack-default-project"
                }
            ]
        }
    ]
