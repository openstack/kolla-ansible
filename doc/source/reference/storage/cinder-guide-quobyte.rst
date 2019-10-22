.. _cinder-guide-quobyte:

=============================
Quobyte Storage for OpenStack
=============================

Quobyte Cinder Driver
~~~~~~~~~~~~~~~~~~~~~

To use the ``Quobyte`` Cinder backend, enable and configure the ``Quobyte``
Cinder driver in ``/etc/kolla/globals.yml``.

.. code-block:: yaml

   enable_cinder_backend_quobyte: "yes"

.. end

Also set values for ``quobyte_storage_host`` and ``quobyte_storage_volume`` in
``/etc/kolla/globals.yml`` to the hostname or IP address of the Quobyte
registry and the Quobyte volume respectively.

Since ``Quobyte`` is proprietary software that requires a license, the use of
this backend requires the ``Quobyte`` Client software package to be installed
in the ``cinder-volume`` and ``nova-compute`` containers. To do this follow the
steps outlined in the :kolla-doc:`Building Container Images
<admin/image-building.html>`,
particularly the ``Package Customisation`` and ``Custom Repos`` sections. The
repository information is available in the ``Quobyte`` customer portal.
