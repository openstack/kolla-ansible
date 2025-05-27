============================
So You Want to Contribute...
============================

For general information on contributing to OpenStack, please check out the
`contributor guide <https://docs.openstack.org/contributors/>`_ to get started.
It covers all the basics that are common to all OpenStack projects: the
accounts you need, the basics of interacting with our Gerrit review system,
how we communicate as a community, etc.

Below will cover the more project specific information you need to get started
with Kolla Ansible.

Basics
~~~~~~

The source repository for this project can be found at:

   https://opendev.org/openstack/kolla-ansible

Communication
~~~~~~~~~~~~~

Kolla Ansible shares communication channels with Kolla.

IRC Channel
    ``#openstack-kolla`` (`channel logs`_) on `OFTC <http://oftc.net>`_

Weekly Meetings
    On Wednesdays in the IRC channel (`meeting information`_)

Mailing list (prefix subjects with ``[kolla]``)
    http://lists.openstack.org/pipermail/openstack-discuss/

Meeting Agenda
    https://wiki.openstack.org/wiki/Meetings/Kolla

Whiteboard (etherpad)
    Keeping track of CI gate status, release status, stable backports,
    planning and feature development status.
    https://etherpad.openstack.org/p/KollaWhiteBoard

.. _channel logs: http://eavesdrop.openstack.org/irclogs/%23openstack-kolla/
.. _meeting information: https://meetings.opendev.org/#Kolla_Team_Meeting

Contacting the Core Team
~~~~~~~~~~~~~~~~~~~~~~~~

In general it is suggested to use the above mentioned public communication
channels, but if you find that you need to contact someone from the Core team
directly, you can find the lists in Gerrit:

- kolla-core https://review.opendev.org/admin/groups/28d5dccfccc125b3963f76ab67e256501565d52b,members
- kayobe-core https://review.opendev.org/admin/groups/361e28280e3a06be2997a5aa47a8a11d3a8fb9b9,members

New Feature Planning
~~~~~~~~~~~~~~~~~~~~

New features are discussed via IRC or mailing list (with [kolla] prefix).
Kolla project keeps blueprints in `Launchpad <https://blueprints.launchpad.net/kolla-ansible>`__.
Specs are welcome but not strictly required.

Task Tracking
~~~~~~~~~~~~~

Kolla project tracks tasks in `Launchpad <https://bugs.launchpad.net/kolla-ansible>`__.
Note this is the same place as for bugs.

If you're looking for some smaller, easier work item to pick up and get started
on, search for the 'low-hanging-fruit' tag.

A more lightweight task tracking is done via etherpad - `Whiteboard <https://etherpad.openstack.org/p/KollaWhiteBoard>`__.

Reporting a Bug
~~~~~~~~~~~~~~~

You found an issue and want to make sure we are aware of it? You can do so
on `Launchpad <https://bugs.launchpad.net/kolla-ansible>`__.
Note this is the same place as for tasks.

Getting Your Patch Merged
~~~~~~~~~~~~~~~~~~~~~~~~~

Most changes proposed to Kolla Ansible require two +2 votes from core reviewers
before +W. A release note is required on most changes as well. Release notes
policy is described in :ref:`its own section <release-notes>`.

Significant changes should have documentation and testing provided with them.

Project Team Lead Duties
~~~~~~~~~~~~~~~~~~~~~~~~

All common PTL duties are enumerated in the `PTL guide <https://docs.openstack.org/project-team-guide/ptl.html>`_.
Kolla Ansible-specific PTL duties are listed in `Kolla Ansible PTL guide <https://docs.openstack.org/kolla-ansible/latest/contributor/ptl-guide.html>`_.
