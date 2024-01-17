.. _skyline-guide:

===========================
Skyline OpenStack dashboard
===========================

Skyline is a dashboard for Openstack with a modern technology stack.

Single Sign On (SSO)
~~~~~~~~~~~~~~~~~~~~

Skyline supports SSO with an Openid IdP. When you configure an IdP with
protocol openid, Kolla will automatically enable SSO and set up the trusted
dashboard url for Keystone. If you don't want to use SSO in Skyline, you can
disable it by setting ``skyline_enable_sso`` to "no":

.. code-block:: yaml

   skyline_enable_sso: "no"

If you want to enable it without setting up the IdP with Kolla you can simply
enable it with:

.. code-block:: yaml

   skyline_enable_sso: "yes"
