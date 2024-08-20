.. cinder-guide-Lightbits:

=====================================
Lightbits labs storage for OpenStack
=====================================

Lightbits labs Cinder Driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use the ``Lightbits labs`` Cinder backend, enable and
configure the ``Lightbits labs`` Cinder driver in
``/etc/kolla/globals.yml``.

.. code-block:: yaml

  enable_cinder_backend_lightbits: "yes"

.. end

Also set the values for the following parameters in ``/etc/kolla/globals.yml``:

- ``lightos_api_address``
- ``lightos_api_port``
- ``lightos_default_num_replicas``
- ``lightos_skip_ssl_verify``
- ``lightos_jwt``


For details on how to use these parameters, refer to the
`Lightbits labs Cinder Reference Guide <https://docs.openstack.org/cinder/latest/configuration/block-storage/drivers/lightbits-lightos-driver.html>`_.

There are numerous other parameters that can be set for this driver and
these are detailed in the above link.
