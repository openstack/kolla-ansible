.. _running-tests:

=============
Running tests
=============

Kolla-ansible contains a suit of tests in the ``tests`` directory.

Any proposed code change in gerrit is automatically rejected by the
`Zuul CI system <https://docs.openstack.org/infra/system-config/zuulv3.html>`__
if the change causes test failures.

It is recommended for developers to run the test suite before submitting patch
for review. This allows to catch errors as early as possible.

Preferred way to run the tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The preferred way to run the unit tests is using ``tox``. It executes tests in
isolated environment, by creating separate virtualenv and installing
dependencies from the ``requirements.txt``, ``test-requirements.txt`` and
``doc/requirements.txt`` files, so the only package you install is ``tox``
itself:

.. code-block:: console

   pip install tox

For more information, see `the unit testing section of the Testing wiki page
<https://wiki.openstack.org/wiki/Testing#Unit_Tests>`_. For example:

To run the default set of tests:

.. code-block:: console

   tox

To run the Python 3.8 tests:

.. code-block:: console

   tox -e py38

To run the style tests:

.. code-block:: console

   tox -e linters

To run multiple tests separate items by commas:

.. code-block:: console

   tox -e py38,linters

Running a subset of tests
-------------------------

Instead of running all tests, you can specify an individual directory, file,
class or method that contains test code, i.e. filter full names of tests by a
string.

To run the tests located only in the ``kolla-ansible/tests``
directory use:

.. code-block:: console

   tox -e py38 kolla-ansible.tests

To run the tests of a specific file
``kolla-ansible/tests/test_kolla_container.py``:

.. code-block:: console

   tox -e py38 test_kolla_container

To run the tests in the ``ModuleArgsTest`` class in
the ``kolla-ansible/tests/test_kolla_container.py`` file:

.. code-block:: console

   tox -e py38 test_kolla_container.ModuleArgsTest

To run the ``ModuleArgsTest.test_module_args`` test method in
the ``kolla-ansible/tests/test_kolla_container.py`` file:

.. code-block:: console

   tox -e py38 test_kolla_container.ModuleArgsTest.test_module_args

Debugging unit tests
--------------------

In order to break into the debugger from a unit test we need to insert
a breaking point to the code:

.. code-block:: python

   import pdb; pdb.set_trace()

Then run ``tox`` with the debug environment as one of the following:

.. code-block:: console

   tox -e debug
   tox -e debug test_file_name.TestClass.test_name

For more information, see the :oslotest-doc:`oslotest documentation
<user/features.html#debugging-with-oslo-debug-helper>`.
