==============
Support Matrix
==============

Supported Operating Systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible supports the following host Operating Systems (OS):

.. note::

   CentOS Stream 9 is supported as a host OS while Kolla does not publish CS9
   based images. Users can build them on their own. We recommend using Rocky
   Linux 9 images instead.

* CentOS Stream 9
* Debian Bookworm (12)
* Rocky Linux 9
* Ubuntu Jammy (22.04)

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
