.. cinder-guide-pure:

=====================================
Pure Storage FlashArray for OpenStack
=====================================

Pure Storage FlashArray Cinder Driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use the ``Pure Storage FlashArray iSCSI`` Cinder backend, enable and
configure the ``FlashArray iSCSI`` Cinder driver in ``/etc/kolla/globals.yml``.

.. code-block:: yaml

  enable_cinder_backend_pure_iscsi: "yes"

.. end

To use the ``Pure Storage FlashArray FC`` Cinder backend, enable and
configure the ``FlashArray FC`` Cinder driver in ``/etc/kolla/globals.yml``.

.. code-block:: yaml

  enable_cinder_backend_pure_fc: "yes"

.. end

It is important to note that you cannot mix iSCSI and FC Pure Storage
FlashArray drivers in the same OpenStack cluster.

Also set the values for the following parameters in ``/etc/kolla/globals.yml``:

- ``pure_api_token``
- ``pure_san_ip``

For details on how to use these parameters, refer to the
`Pure Storage Cinder Reference Guide<https://docs.openstack.org/cinder/latest/configuration/block-storage/drivers/pure-storage-driver.html>__`.

There are numerous other parameters that can be set for this driver and
these are detailed in the above link.

If you wish to use any of these parameters then refer to the
`Service Configuration<https://docs.openstack.org/kolla-ansible/latest/admin/advanced-configuration.html#openstack-service-configuration-in-kolla>__`
documentation for instructions using the INI update strategy.

The use of this backend requires that the ``purestorage`` SDK package is
installed in the ``cinder-volume`` container. To do this follow the steps
outlined in the `kolla image building guide<https://docs.openstack.org/kolla/latest/admin/image-building.html>__`
particularly the ``Package Customisation`` and ``Custom Repos`` sections.
