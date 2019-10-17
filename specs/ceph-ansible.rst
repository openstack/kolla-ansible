..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Moving to ceph-ansible for Kolla
=================================

It has been discussed within the Kolla community that we should look at moving
from our own orchestration and containers for Ceph to those provided by the
'ceph-ansible' project. This spec proposes how this should happen.

Problem description
===================

Ceph is a complex project that exists outside of OpenStack. As new versions of
Ceph are released, the Kolla community have had to spend time and resources
ensuring that our implementation is up to date, upgrade works correctly, etc,
in addition to the multiple OpenStack services we support. Meanwhile, there are
other existing projects that work just on Ceph, and can potentially do this
much better.

Use cases
---------

1. Ceph deployment using dedicated Storage nodes
2. Ceph deployment using HCI nodes (storage nodes on compute nodes)

Proposed change
===============

ceph-ansible is one such project that is part of the official Ceph
project namespace[0]. This gives us a reasonable degree of certainty that it
can provide a more complete and well maintained implementation of Ceph than
Kolla can provide on its own.

Alternatives
------------

Continue to maintain current approach i.e. Ceph deployment in kolla-ansible.

Other End User impact
---------------------

We will need to move to images that ceph-ansible supports, we have two options:

1. Directly use what is available on docker hub[1].
2. Build images using ceph-container repo[2].

NOTE: Currently ceph-container project does not support Ubuntu container images.

Security impact
---------------

From a high level this should not have any security impact. It is possible
security would be even improved over what we have now, due to the active
community maintaining the ceph-ansible project[3].

Performance Impact
------------------

We see no potential performance impact. The time for deploying ceph-ansible may
end up being slightly longer or shorter when compared to Kolla's Ceph, but the
difference should not be big.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mnasiadka

Milestones
----------

Target Milestone for completion:
  U

Work Items
----------

1. Mark the current implementation of Ceph in Kolla as deprecated in the Train
   cycle. The ceph-ansible implementation should be ready for the release of
   U.

2. Provide concise documentation on how a Kolla operator should go about
   deploying ceph-ansible in a way that's consistent with Kolla best practices.

3. Ensure we have a sensible and easy to follow upgrade path for those
   currently running Kolla's implementation of Ceph in production.

4. The current Kolla gates for Ceph will need to be updated.

5. (Optional) Create a playbook for ceph-ansible integration - similar to the one OpenStack-Ansible
   project has developed[4].

Testing
=======
See work item number 4 above.

Documentation Impact
====================
See work item number 2 above.

References
==========
[0] http://docs.ceph.com/ceph-ansible/master/
[1] https://hub.docker.com/r/ceph/daemon
[2] https://github.com/ceph/ceph-container
[3] https://github.com/ceph/ceph-ansible/graphs/contributors
[4] https://opendev.org/openstack/openstack-ansible/src/branch/master/playbooks/ceph-install.yml
