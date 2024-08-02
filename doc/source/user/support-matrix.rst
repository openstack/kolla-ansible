==============
Support Matrix
==============

Supported Operating Systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible supports the following host Operating Systems (OS):

.. note::

   CentOS Stream 8 is no longer supported as a host OS. The Yoga release
   supports both CentOS Stream 8 and CentOS Stream 9 / Rocky Linux 9, and
   provides a route for migration.

.. note::

   CentOS Stream 9 is supported as a host OS while Kolla does not publish CS9
   based images. Users can build them on their own. We recommend using Rocky
   Linux 9 images instead.

* CentOS Stream 9
* Debian Bullseye (11)
* Debian Bookworm (12)
* openEuler 22.03 LTS
* Rocky Linux 9
* Ubuntu Jammy (22.04)
* Ubuntu Noble (24.04)

.. note::

  Ubuntu Noble (24.04) can use both Jammy (default) and Noble based Kolla images.
  In order to use the latter - please set ``kolla_base_distro_version`` to
  ``noble`` and ``distro_python_version`` to ``3.12``.

Supported container images
~~~~~~~~~~~~~~~~~~~~~~~~~~

For best results, the base container image distribution should match the host
OS distribution. The following values are supported for ``kolla_base_distro``:

* ``centos``
* ``debian``
* ``rocky``
* ``ubuntu``

For details of which images are supported on which distributions, see the
:kolla-doc:`Kolla support matrix <support_matrix>`.
