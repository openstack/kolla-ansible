==============
Support Matrix
==============

Supported Operating Systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible supports the following host Operating Systems (OS):

* CentOS 7
* CentOS 8
* Debian Buster (10)
* RHEL 7
* RHEL 8
* Ubuntu Bionic (18.04)

Supported container images
~~~~~~~~~~~~~~~~~~~~~~~~~~

For best results, the base container image distribution should match the host
OS distribution. The following values are supported for ``kolla_base_distro``:

* ``centos``
* ``debian``
* ``rhel``
* ``ubuntu``

For details of which images are supported on which distributions, see the
:kolla-doc:`Kolla support matrix <support_matrix>`.

CentOS 8
--------

For details on how to build images for CentOS 8, see the :kolla-doc:`Kolla
image building guide <admin/image-building.html#building-kolla-images>`. Note
that for the Train release only, Kolla Ansible applies a ``-centos8`` suffix
(configured via ``openstack_tag_suffix``) to image tags by default on CentOS 8
hosts. The default tag is therefore ``train-centos8``. This is to
differentiate CentOS 7 and CentOS 8 container images. Information about
migrating from CentOS 7 to CentOS 8 will be provided soon.
