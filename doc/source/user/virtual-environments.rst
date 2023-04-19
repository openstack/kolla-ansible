.. _virtual-environments:

====================
Virtual Environments
====================

Python `virtual environments <https://docs.python.org/3/library/venv.html>`_
provide a mechanism for isolating python packages from the system site packages
and other virtual environments. Kolla-ansible largely avoids this problem by
deploying services in Docker containers, however some python dependencies must
be installed both on the Ansible control host and the target hosts.

Kolla Ansible supports the default Python 3 versions provided by the
:kolla-ansible-doc:`supported Operating Systems <user/support-matrix>`. For
more information see `tested runtimes <|TESTED_RUNTIMES_GOVERNANCE_URL|>`_.

Ansible Control Host
====================

The kolla-ansible python package and its dependencies may be installed in a
python virtual environment on the Ansible control host. For example:

.. code-block:: console

   python3 -m venv /path/to/venv
   source /path/to/venv/bin/activate
   pip install -U pip
   pip install kolla-ansible
   pip install 'ansible>=6,<8'
   deactivate

To use the virtual environment, it should first be activated:

.. code-block:: console

   source /path/to/venv/bin/activate
   (venv) kolla-ansible --help

The virtual environment can be deactivated when necessary:

.. code-block:: console

   (venv) deactivate

Note that the use of a virtual environment on the Ansible control host does not
imply that a virtual environment will be used for execution of Ansible modules
on the target hosts.

.. _virtual-environments-target-hosts:

Target Hosts
============

Ansible supports remote execution of modules in a python virtual environment
via the ``ansible_python_interpreter`` variable. This may be configured to be
the path to a python interpreter installed in a virtual environment.  For
example:

.. code-block:: yaml

   ansible_python_interpreter: /path/to/venv/bin/python

Note that ``ansible_python_interpreter`` cannot be templated.

Kolla-ansible provides support for creating a python virtual environment on the
target hosts as part of the ``bootstrap-servers`` command. The path to the
virtualenv is configured via the ``virtualenv`` variable, and access to
site-packages is controlled via ``virtualenv_site_packages``. Typically we
will need to enable use of system site-packages from within this virtualenv, to
support the use of modules such as yum, apt, and selinux, which are not
available on PyPI.

When executing kolla-ansible commands other than ``bootstrap-servers``, the
variable ``ansible_python_interpreter`` should be set to the python interpreter
installed in ``virtualenv``.
