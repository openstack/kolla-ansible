.. _manila-vast-guide:

==========================================================
VAST Manila Driver for OpenStack
==========================================================

VAST Share Driver integrates OpenStack with VAST Data's Storage System.
Shares in the Shared File System service are mapped to directories
on VAST, and are accessed via NFS protocol using a Virtual IP Pool.

For more details on how to use the VAST driver, refer to the
`VAST share driver docs <https://docs.openstack.org/manila/latest/configuration/shared-file-systems/drivers/vastdata_driver.html>`_.

Configuration on Kolla deployment
---------------------------------

Enable Manila and the VAST driver in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_manila: true
   enable_manila_backend_vast: true

In ``/etc/kolla/globals.yml`` you must set:

.. code-block:: yaml

   manila_vast_vippool_name: "<virtual IP pool name>"

You must ensure that the VAST host and port are correct. This
may done via shared settings in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   vast_host: "<hostname or IP for VAST REST API>"
   vast_port: 443

or if the VAST appliance is not shared with Cinder:

.. code-block:: yaml

   manila_vast_host: "<hostname or IP for VAST REST API>"
   manila_vast_port: 443

Authentication
~~~~~~~~~~~~~~

API token authentication is preferred over username and password. To use
an API token, set the following in ``/etc/kolla/passwords.yml``:

.. code-block:: yaml

   manila_vast_api_token: "<api token>"

Alternatively, username and password authentication may be used. Set the
username in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   manila_vast_user: "<username>"

And the password in ``/etc/kolla/passwords.yml``:

.. code-block:: yaml

   manila_vast_password: "<password>"

In ``/etc/kolla/globals.yml`` you can optionally customise:

.. code-block:: yaml

   manila_vast_root_export: "manila"

The driver assumes tenant networks that wish to mount
their VAST backed NFS file shares are able to route to the
VAST virtual IP pool you have chosen.
By default, the driver will create shares under
``/manila`` base export on VAST.
