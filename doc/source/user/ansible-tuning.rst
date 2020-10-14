==============
Ansible tuning
==============

In this section we cover some options for tuning Ansible for performance and
scale.

SSH pipelining
--------------

SSH pipelining is disabled in Ansible by default, but is generally safe to
enable, and provides a reasonable performance improvement.

.. code-block:: ini
   :caption: ``ansible.cfg``

   [ssh_connection]
   pipelining = True

Forks
-----

By default Ansible executes tasks using a fairly conservative 5 process forks.
This limits the parallelism that allows Ansible to scale. Most Ansible control
hosts will be able to handle far more forks than this. You will need to
experiment to find out the CPU, memory and IO limits of your machine.

For example, to increase the number of forks to 20:

.. code-block:: ini
   :caption: ``ansible.cfg``

   [defaults]
   forks = 20

Fact caching
------------

By default, Ansible gathers facts for each host at the beginning of every play,
unless ``gather_facts`` is set to ``false``. With a large number of hosts this
can result in a significant amount of time spent gathering facts.

One way to improve this is through Ansible's support for `fact caching
<https://docs.ansible.com/ansible/latest/user_guide/playbooks_variables.html#caching-facts>`__.
In order to make this work with Kolla Ansible, it is necessary to change
Ansible's `gathering
<https://docs.ansible.com/ansible/latest/reference_appendices/config.html#default-gathering>`__
configuration option to ``smart``.

Example
~~~~~~~

In the following example we configure Kolla Ansible to use fact caching using
the `jsonfile cache plugin
<https://docs.ansible.com/ansible/latest/plugins/cache/jsonfile.html>`__.

.. code-block:: ini
   :caption: ``ansible.cfg``

   [defaults]
   gathering = smart
   fact_caching = jsonfile
   fact_caching_connection = /tmp/ansible-facts

You may also wish to set the expiration timeout for the cache via ``[defaults]
fact_caching_timeout``.
