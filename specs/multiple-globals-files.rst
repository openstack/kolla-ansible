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

======================================
Add support for multiple globals files
======================================

https://blueprints.launchpad.net/kolla-ansible/+spec/multiple-globals-files

Adding this feature to the kolla-ansible script, which will make it, automatically,
read multiple globals files. This would give operators the ability to have
separate globals files for some services, giving them a bit more granular control,
without the need to add the ``-e @/path/to/file`` flag. These files will be placed
under a new ``/etc/kolla/globals.d`` directory and ``kolla-ansible`` will search
for ``globals.d/*.yml`` files. The main ``globals.yml`` file will still exist
under ``/etc/kolla``, as usual.

Problem description
===================

There's no problem, per say, to solve. This feature will basically give operators
the ability to have separate globals files for some services, giving them a bit
more granular control, without the need to add the ``-e @/path/to/file`` flag.

Use cases
---------
1. Allow a more granular controller over individual service's options
2. Better file and directory structure

Proposed change
===============

- Add the capability in the ``tools/kolla-ansible`` script
  - Check if the ``globals.d`` directory exists
  - If it is, add its files in the ``CONFIG_OPTS`` variable at the end of the ``tools/kolla-ansible`` script

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

Konstantinos Mouzaitis <kon.mouzakitis@vscaler.com>

Milestones
----------

Target Milestone for completion:
  ussuri-10.0.0

Work Items
----------

- Add the capability in the ``tools/kolla-ansible`` script
  - Check if the ``globals.d`` directory exists
  - If it is, add its files in the ``CONFIG_OPTS`` variable at the end of the ``tools/kolla-ansible`` script

Testing
=======
Test the new kolla-ansible script when the ``globals.d`` directory exists and
includes some more yml files, as well as when it doesn't exist.

Documentation Impact
====================
``doc/source/user/quickstart.rst`` will need to be updated to include the options discussed in this feature
