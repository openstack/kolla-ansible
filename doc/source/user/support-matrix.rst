==============
Support Matrix
==============

Supported Operating Systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible supports the following host Operating Systems (OS):

.. note::

   CentOS 7 is no longer supported as a host OS. The Train release supports
   both CentOS 7 and 8, and provides a route for migration. See the `Kolla
   Ansible Train documentation
   <https://docs.openstack.org/kolla-ansible/train/user/centos8.html>`_ for
   information on migrating to CentOS 8.

.. note::

   CentOS Linux 8 (as opposed to CentOS Stream 8) is no longer supported as a
   host OS. The Victoria release will in future support both CentOS Linux 8 and
   CentOS Stream 8, and provides a route for migration.

.. note::

   CentOS Stream 9 is supported as a host OS while Kolla does not publish CS9
   based images. Users can build them on their own. We recommend using Rocky
   Linux 9 images instead.



* CentOS Stream 9
* Debian Bullseye (11)
* openEuler 22.03 LTS
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
