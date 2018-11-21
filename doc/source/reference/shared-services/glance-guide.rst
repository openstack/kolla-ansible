.. _glance-guide:

======================
Glance - Image service
======================

Glance backends
---------------

Overview
~~~~~~~~

Glance can be deployed using Kolla and supports the following
backends:

* file
* ceph
* vmware
* swift

File backend
~~~~~~~~~~~~

When using the ``file`` backend, images will be stored locally
under the value of the ``glance_file_datadir_volume`` variable, which defaults
to a docker volume called ``glance``. By default when using ``file`` backend
only one ``glance-api`` container can be running.

For better reliability and performance, ``glance_file_datadir_volume`` should
be mounted under a shared filesystem such as NFS.

Usage of glance file backend under shared filesystem:

.. code-block:: yaml

   glance_backend_file: "yes"
   glance_file_datadir_volume: "/path/to/shared/storage/"

Ceph backend
~~~~~~~~~~~~

To make use of ``ceph`` backend in glance, simply enable ceph or external ceph.
By default will enable backend ceph automatically.
Please refer to :doc:`../storage/ceph-guide`
or :doc:`../storage/external-ceph-guide` on how to configure this backend.

To enable the ceph backend manually:

.. code-block:: yaml

   glance_backend_ceph: "yes"

VMware backend
~~~~~~~~~~~~~~

To make use of VMware datastores as a glance backend,
enable `glance_backend_vmware` and refer to :doc:`../compute/vmware-guide` for
further VMware configuration.

To enable the vmware backend manually:

.. code-block:: yaml

   glance_backend_vmware: "yes"

Swift backend
~~~~~~~~~~~~~

To store glance images in a swift cluster, the ``swift`` backend should
be enabled.  Refer to :doc:`../storage/swift-guide` on how to configure
swift in kolla.
If ceph is enabled, will have higher precedence over swift as glance backend.

To enable the swift backend manually:

.. code-block:: yaml

   glance_backend_swift: "yes"

Upgrading glance
----------------

Overview
~~~~~~~~

Glance can be upgraded with the following methods:

* Rolling upgrade
* Legacy upgrade

Rolling upgrade
~~~~~~~~~~~~~~~

As of the Rocky release, glance can be upgraded in a rolling upgrade mode.
This mode will reduce the API downtime during upgrade to a minimum of
a container restart, aiming for zero downtime in future releases.

By default it is disabled, so if you want to upgrade using this mode it will
need to be enabled.

.. code-block:: yaml

   glance_enable_rolling_upgrade: "yes"

.. warning::

    When using glance backend ``file`` without a shared filesystem, this method cannot
    be used or will end up with a corrupt state of glance services.
    Reasoning behind is because glance api is only running in one host, blocking the
    orchestration of a rolling upgrade.

Legacy upgrade
~~~~~~~~~~~~~~

This upgrade method will stop APIs during database schema migrations,
and container restarts.

It is the default mode, ensure rolling upgrade method is not enabled.

.. code-block:: yaml

   glance_enable_rolling_upgrade: "no"


Other configuration
-------------------

Glance cache
~~~~~~~~~~~~

Glance cache is disabled by default, it can be enabled by:

.. code-block:: yaml

   enable_glance_image_cache: "yes"
   glance_cache_max_size: "10737418240" # 10GB by default

.. warning::

   When using the ceph backend, is recommended to not use glance cache, since
   nova already has a cached version of the image, and the image is directly
   copied from ceph instead of glance api hosts. Enabling glance cache will
   lead to unnecessary storage consumption.

Glance caches are not cleaned up automatically, the glance team recommends to
use a cron service to regularly clean cached images. In the future kolla will
deploy a cron container to manage such clean ups.  Please refer to `Glance
image cache <https://docs.openstack.org/glance/latest/admin/cache.html>`__.
