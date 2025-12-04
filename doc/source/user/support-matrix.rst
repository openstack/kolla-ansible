==============
Support Matrix
==============

Supported Operating Systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible supports the following host Operating Systems (OS):

.. note::

   CentOS Stream 9 and 10 is supported as a host OS while Kolla does not
   publish CS9/10 based images. Users can build them on their own. We recommend
   using Rocky and 10 images instead.

* CentOS Stream 9
* CentOS Stream 10
* Debian Bookworm (12)
* Rocky Linux 9
* Ubuntu Noble (24.04)

Supported container images
~~~~~~~~~~~~~~~~~~~~~~~~~~

For best results, the base container image distribution should match the host
OS distribution. The following values are supported for ``kolla_base_distro``:

* ``centos``
* ``debian``
* ``rocky``
* ``ubuntu``

.. note::

   In order to use CentOS Stream 10 please set ``kolla_base_distro_version``
   to ``stream10`` and to ``10`` for using Rocky Linux 10.

For details of which images are supported on which distributions, see the
:kolla-doc:`Kolla support matrix <support_matrix>`.
