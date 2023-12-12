Install openstack clients required for Kolla-Ansible CI scripts.
The defaults are suitable for CI environment.

**Role Variables**

.. zuul:rolevar:: openstack_clients_pip_packages

   List of dictionaries, with package and enabled keys, e.g.:
   - package: python-barbicanclient
     enabled: true

.. zuul:rolevar:: openstack_clients_venv_base

   Directory used as base for python venv

.. zuul:rolevar:: openstack_clients_venv_name

   Name of python venv to use for package installations
