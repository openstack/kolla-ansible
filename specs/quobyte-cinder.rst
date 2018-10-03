..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Add support for Quobyte cinder backend
======================================

https://blueprints.launchpad.net/kolla-ansible/+spec/cinder-quobyte-backend

Currently there is no option to enable the use of Quobyte as a backend for Cinder
within kolla. Since there is support for Quobyte in Cinder and Nova, it should be
a valid option in Kolla as well.

Problem description
===================

Quobyte is a software defined storage solution that has a Cinder driver allowing
it to be used with Cinder and Nova. Currently there is no option in Kolla to
enable the use of Quobyte in Cinder and Nova.

Use cases
---------
Allowing the use of a Quobyte volume as a backend for Cinder in Kolla.

Proposed change
===============

- Add an ``enable_cinder_backend_quobyte`` option to ``etc/kolla/globals.yml``
- If enabled, add the shared propagation to the ``/var/lib/nova/mnt`` bind, same as NFS.
  This would require extending the logic in ``ansible/roles/nova/defaults/main.yml`` to
  check if either NFS or Quobyte are enabled as Cinder backends.
- Update documentation in ``doc/source/reference/cinder-guide.rst`` to include configuration
  of the Quobyte Cinder driver.

Security impact
---------------
None

Performance Impact
------------------
None


Implementation
==============

Assignee(s)
-----------

Patrick O'Neill <patrick.oneill@vscaler.com>

Milestones
----------

Target Milestone for completion:
  stein-1

Work Items
----------

1. Create variable in globals.yml to allow Cinder Quobyte backend to be enabled.
2. Define Quobyte as a valid backend option in prechecks task.
3. Add shared propagation to docker bind mounts in Nova.
4. Update documentation to cover Cinder and Nova driver configuration for Quobyte.

Testing
=======
Following the cinder reference of kolla to use quobyte as cinder backend. Perform
checks to ensure that the backend is functional by creating volumes in cinder
and mounting volumes to instances.

Documentation Impact
====================
``doc/source/reference/cinder-guide.rst`` needs to be updated to include a section
on Quobyte driver configuration.
