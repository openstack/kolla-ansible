=====================================
Continuous Integration (CI) & Testing
=====================================

Kolla-Ansible uses
`Zuul <https://zuul.openstack.org/buildsets?project=openstack%2Fkolla-ansible&branch=master&pipeline=check>`__
for continuous integration. Similar to testing performed using
`devstack <https://docs.openstack.org/devstack/latest/>`__, Kolla-Ansible is
capable of integrating and testing pre-merged dependencies from many other
projects.

Debugging with ARA in CI
~~~~~~~~~~~~~~~~~~~~~~~~

Frequently, the need arises to obtain more verbose ansible logging in CI.
`ARA <https://ara.recordsansible.org/>`__ is an ansible plugin that collects a
large amount of execution information and can render it into a browser
friendly format.

This plugin is not enabled by default because there is a per-task overhead.
However, it's possible to trigger it when trying to debug a failing job.

By adding the text `#ara` to the git commit message of the review, the CI jobs
will enable the plugin and generate a sqlite database containing comprehensive
logging. It's possible to render an HTML version of this by using
`#ara_verbose`. Generating the HTML is not very efficient, however, and
consumes a large amount of logging resources.

Please note that git usually strips lines beginning with `#` from the commit
message. This can be avoided by preceding the string with a space.

CI coverage matrix
~~~~~~~~~~~~~~~~~~

Zuul job templates live in ``zuul.d`` and are applied in
``zuul.d/project.yaml``. Pipelines always run tox/python style+unit checks,
docs/release builds, and requirements checks; the matrix below shows the
scenario jobs in ``check``/``gate``.

.. csv-table:: Scenario matrix
   :header-rows: 1
   :file: ci-matrix.csv
   :widths: 12 7 7 7 7 7 7 7 7 7 7 7 7 12
   :delim: ;

Legend: ✅ = covered, ❌ = disabled, – = not covered. ``Core`` means the standard
Keystone/Glance/Neutron/Nova/Heat stack is deployed; ``Tempest`` indicates
smoke tests run; ``SLURP`` = Skip Level Upgrade Release Process.
