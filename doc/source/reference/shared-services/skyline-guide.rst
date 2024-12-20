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

Customize logos
~~~~~~~~~~~~~~~

To change some of the logos used by Skyline you can overwrite the default
logos. Not all images can be replaced, you can change the browser icon, the
two logos on the login screen and the logo in the header once you are logged
in.

To overwrite the files create the directory
``{{ node_custom_config }}/skyline/logos`` and place the files you want to use
there.

Make sure you have the correct filenames and directory structure as described
below.

Additionally add the files or directories you created to
``skyline_custom_logos``, a list of files or directories that will be copied
inside the container.

.. list-table:: Logos/images that can be overwritten
   :widths: 30 70
   :header-rows: 1

   * - Logo/image
     - Path in ``{{ node_custom_config }}/skyline/logos``
   * - Browser Icon
     - ./favicon.ico
   * - Login page left logo
     - ./asset/image/logo.png
   * - Login page right logo
     - ./asset/image/loginRightLogo.png
   * - Logo header logged in
     - ./asset/image/cloud-logo.svg


To replace only the browser icon set

.. code-block:: yaml

   skyline_custom_logos: ["favicon.ico"]

To replace files in ``asset`` set

.. code-block:: yaml

   skyline_custom_logos: ["asset"]

To replace all use

.. code-block:: yaml

   skyline_custom_logos: ["asset", "favicon.ico"]

Since the files are overwritten inside the container, you have to remove the
container and recreate it if you want to revert to the default logos. Just
removing the configuration will not remove the files.

External Swift
~~~~~~~~~~~~~~

If you are running an external Swift compatible object store you can add
it to the skyline dashboard. Since Skyline can not use Keystone's
endpoint api, you have to tell it the url of your external service.

You have to set ``skyline_external_swift`` and
``skyline_external_swift_url`` in your configuration:

.. code-block:: yaml

   skyline_external_swift: "yes"
   skyline_external_swift_url: "https://<your-host>/swift"
