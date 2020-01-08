..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

..
 This template should be in ReSTructured text. The filename in the git
 repository should match the launchpad URL, for example a URL of
 https://blueprints.launchpad.net/kolla/+spec/awesome-thing should be named
 awesome-thing.rst . Please do not delete any of the sections in this
 template. If you have nothing to say for a whole section, just write: None
 For help with syntax, see http://www.sphinx-doc.org/en/stable/rest.html
 To test out your formatting, see http://www.tele3.cz/jbar/rest/rest.html

==================
CentOS 8 Migration
==================

https://blueprints.launchpad.net/kolla/+spec/centos-rhel-8
https://blueprints.launchpad.net/kolla-ansible/+spec/centos-rhel-8

CentOS 8 is here, and RDO support for CentOS 7 is going away.

Problem description
===================

This spec is largely focussed on the issue of migrating running systems from
CentOS 7 to CentOS 8. We will not in general look at the details of porting
Kolla to CentOS 8 here.

Kolla images
------------

Train is the last release of OpenStack to support Python 2. Since CentOS 7
provides only limited support for Python 3, RDO plans to support only CentOS 8
for the Ussuri cycle.

While RDO Train initially only provided Python 2 based RPMs for CentOS 7, it is
expected that Python 3 based Train RPMs will be made available for CentOS 8. We
should therefore support building Train images with either CentOS 7 or CentOS 8
as a base. Both sets of images should be published to Dockerhub. The image
naming scheme will need to take account of the OS version, which it currently
does not.

Kolla Ansible
-------------

There is no supported upgrade path between CentOS 7 and 8 hosts - a full
reinstall is necessary. This provides us with one release (Train) that supports
both CentOS 7 and 8, with which we could perform a rolling reinstallation of
hosts. The cloud should continue to operate in this mixed 7/8 mode during the
migration. The following diagram shows an example with 6 hosts h1 to h6 being
migrated in batches of two::

         h1 h2 h3 h4 h5 h6
       -------------------
    t0 | c7 c7 c7 c7 c7 c7
    t1 | c8 c8 c7 c7 c7 c7
    t2 | c8 c8 c8 c8 c7 c7
    t3 | c8 c8 c8 c8 c8 c8

Proposed change
===============

Kolla images - Ussuri
---------------------

Support for building CentOS 8 based container images will be added to Kolla
during the Ussuri cycle. Initially, this will exist in parallel with CentOS 7
support, and be controlled via the ``distro-package-manager`` configuration
option, which takes its default value from the base image tag (``7.*`` for
``yum``, ``8.*`` for ``dnf``).

New build and publishing CI jobs will be added for CentOS 8. We will use an
alternative Docker image tag to tag CentOS 8 images on Dockerhub:
``master-centos8``. An example image name is
``kolla/centos-binary-base:master-centos8``.

Once this work is complete, support for CentOS 7 will be removed. CentOS 8
images will then be tagged as ``master`` (or ``ussuri`` after branching). This
two-phase approach allows for a clean backport to Train. A downside is that
``master-centos8`` tags will continue to exist in Dockerhub after the
transition, which could be confusing for users.

Kolla images - Train
--------------------

The CentOS 8 support developed for Ussuri will be backported to the
stable/train branch. Since these changes are significant, we should advertise
this clearly to users who might not be expecting it on a stable branch.
Train images will be built and published for CentOS 7 and 8, with CentOS 8
images using a tag of ``train-centos8``.

Kolla Ansible - Ussuri
----------------------

Support for deploying CentOS 8 based container images will be added to Kolla
Ansible during the Ussuri cycle. Initially, this will exist in parallel with
CentOS 7 support, and be controlled via Ansible host facts about the host OS
distribution. We will deploy CentOS 7 containers on CentOS 7 hosts, and CentOS
8 containers on CentOS 8 hosts to avoid kernel and userspace incompatibility
issues. This also aligns with the `migration plan
<http://lists.openstack.org/pipermail/openstack-discuss/2019-November/011133.html>`__
proposed by Tripleo.

During the migration, we may have a mix of CentOS 7 hosts running CentOS 7
containers, and CentOS 8 hosts running CentOS 8 containers.

The image tag used will need to depend on the host OS. We have a hierarchy of
image tag variables, for example: the ``nova-compute`` container uses a tag
defined by ``nova_compute_tag``, which defaults to ``nova_tag``, which defaults
to ``openstack_release``.

To preserve the usage of ``openstack_release``, a new intermediate variable
will be introduced. In this new scheme, the ``nova-compute`` container uses a
tag defined by ``nova_compute_tag``, which defaults to ``nova_tag``, which
defaults to ``openstack_tag``, which defaults to ``openstack_release ~
'-centos8'`` on CentOS 8, or ``openstack_release`` otherwise. Providing this
suffix as a variable would help users who are using more fine-grained image
tags (e.g. ``nova_compute_tag``).

Once this work is complete, support for CentOS 7 will be removed. The
intermediate variable ``openstack_tag`` will remain, but will always default to
``openstack_release``.

Kolla Ansible - Train
---------------------

The CentOS 8 support developed for Ussuri will be backported to the
stable/train branch. Since these changes are significant, we should advertise
this clearly to users who might not be expecting it on a stable branch.

Kolla Ansible - Rolling Migration
---------------------------------

In order to keep the cloud functional during the migration, the changes will be
rolled through in batches. The size and scope of the batches are to be
determined by the operator, but we should provide some guidance on selecting
batches safely to avoid losing quorum of clustered services or reducing service
availability below some minimum threshold. Provisioning of the new OS is out of
the scope of this discussion, but could be handled by Kayobe or another tool.

We should treat each batch as a removal of a set of hosts followed by an
addition of new set of hosts. This is a good opportunity for us to tidy up
these procedures and fill in gaps where necessary.

To remove a batch of hosts:

#. Migrate running OpenStack resources from the hosts to other hosts which are
   not in the batch. This includes compute instances (VMs), storage (Swift
   disks), network services (DHCP & L3 agents etc.). Ideally this would be
   automated, but should at least be discussed in documentation
#. Cleanly disable (if necessary) and shutdown running OpenStack services
#. Shutdown hosts

The hosts should then be provisioned with CentOS 8 - as mentioned this is out
of scope. Then to add a batch of hosts:

#. Provision CentOS 8 to hosts (out of scope)
#. Bootstrap hosts
#. Deploy services
#. Validate new hosts

We may wish to adopt existing data on these hosts, e.g. for Swift a full sync
from empty for each node would take a long time. For systems where Docker
volumes are stored on a separate disk or partition, it may be possible to
preserve these. There may be some corner cases where this does not work well,
and we should check for these and advise in documentation.

For the majority of these tasks it should be possible to use the ``--limit``
argument to speed up the process, but this should be investigated and verified.

Stable upgrades
---------------

Where possible, we should aim to use the same versions of packages on CentOS 7
and 8 for Train. Upgrades should wait until Ussuri. In some cases this may not
be possible, and we should make it clear in release notes where services will
be upgraded in Train.

Given that a rolled migration may take a significant amount of time to
complete, we should consider that services may be partially upgraded. In cases
where this may cause a problem, it should be called out in the documentation,
with any available mitigation (e.g. disable during migration).

Feature removal
---------------

Due to differences between CentOS 7 and 8, it may not be possible or practical
to support all existing features. We should bear in mind that this will apply
to the Train release, and continue to support these features on CentOS 7.

Ceph support
^^^^^^^^^^^^

Migrating a Ceph cluster deployed by Kolla Ansible to CentOS 8 would represent
a significant challenge. Ceph deployment support has been deprecated since the
Stein release, and this is a good point to remove that support.

SCSI target daemon
^^^^^^^^^^^^^^^^^^

For CentOS 7, the SCSI target daemon (``tgtd``) is provided by EPEL. For CentOS
8, this is no longer available, probably due to a preference for the kernel
SCSI target, `LIO <http://linux-iscsi.org/wiki/LIO>`__.  Due to the requirement
to reinstall, this migration provides a good opportunity to stop supporting
``tgtd`` for CentOS. This will affect some Cinder volume drivers, including the
LVM backend. ``tgtd`` will still be supported on Debian/Ubuntu. Note that no
changes are required for the iSCSI initiator.

Security impact
---------------

There should be no security impact due to this change.

Performance Impact
------------------

There should be no performance impact due to this change.

Alternatives
------------

CentOS 7 to 8 upgrade
^^^^^^^^^^^^^^^^^^^^^

There are various documented procedures for upgrading from CentOS 7 to 8
without a reinstall. These typically come with various disclaimers, and are not
recommended for production environments.

Image naming
^^^^^^^^^^^^

Rather than using a different tag to mark CentOS 8 images, it would be possible
to use a base distro of ``centos8``. e.g. ``kolla/centos8-binary-base:master``.
The reason for not doing this is that there is a reasonable amount of logic
both in Kolla and Kolla Ansible that uses the ``base_distro`` which would need
to be updated.

Don't publish master-centos8 tag
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

During the transition period, we could manage with always building images for
CentOS 8 on master, thus avoiding the need for a temporary ``master-centos8``
tag.

Implementation
==============

Assignee(s)
-----------

Primary assignees:
  Marcin Juszkiewicz (hrw)
  Mark Goddard (mgoddard)
  Michal Nasiadka (mnasiadka)
  Radoslaw Piliszek (yoctozepto)

Work Items
----------

Kolla
^^^^^

* Support building CentOS 8 images in Ussuri
* Build and publish both CentOS 7 and 8 images in CI
* Backport CentOS 8 support to Train
* Remove CentOS 7 image support in Ussuri
* Update documentation (image tags etc.)

Kolla Ansible
^^^^^^^^^^^^^

* Support deploying CentOS 8 images in Ussuri
* Test (separately) deployment to both CentOS 7 and 8 in CI
* Backport CentOS 8 support to Train
* Test migration from CentOS 7 to 8 on Train in CI
* Test upgrade from Train to Ussuri on CentOS 8
* Remove CentOS 7 support in Ussuri
* Update documentation (migration)

Testing
=======

This will be tested by parallel build and deploy jobs for CentOS 7 and 8, in
addition to a job testing migration from CentOS 7 to 8. Significant manual
testing will be required to explore edge cases associated with the migration.

Documentation Impact
====================

* Building CentOS 8 images
* Deploying to CentOS 8
* Image tags for CentOS 8
* Migration procedure covered in detail

References
==========

* `CentOS 8 release notes <https://wiki.centos.org/Manuals/ReleaseNotes/CentOS8.1905>`__
