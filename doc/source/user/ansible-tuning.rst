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

Fact variable injection
-----------------------

By default, Ansible injects a variable for every fact, prefixed with
``ansible_``. This can result in a large number of variables for each host,
which at scale can incur a performance penalty. Ansible provides a
`configuration option
<https://docs.ansible.com/ansible/latest/reference_appendices/config.html#inject-facts-as-vars>`__
that can be set to ``False`` to prevent this injection of facts. In this case,
facts should be referenced via ``ansible_facts.<fact>``. In recent releases of
Kolla Ansible, facts are referenced via ``ansible_facts``, allowing users to
disable fact variable injection.

.. code-block:: ini
   :caption: ``ansible.cfg``

   [defaults]
   inject_facts_as_vars = False

Fact filtering
--------------

Ansible facts filtering can be used to speed up Ansible.  Environments with
many network interfaces on the network and compute nodes can experience very
slow processing with Kolla Ansible. This happens due to the processing of the
large per-interface facts with each task.  To avoid storing certain facts, we
can use the ``kolla_ansible_setup_filter`` variable, which is used as the
``filter`` argument to the ``setup`` module. For example, to avoid collecting
facts for virtual interfaces beginning with q or t:

.. code-block:: yaml

   kolla_ansible_setup_filter: "ansible_[!qt]*"

This causes Ansible to collect but not store facts matching that pattern, which
includes the virtual interface facts. Currently we are not referencing other
facts matching the pattern within Kolla Ansible.  Note that including the
``ansible_`` prefix causes meta facts ``module_setup`` and ``gather_subset`` to
be filtered, but this seems to be the only way to get a good match on the
interface facts.

The exact improvement will vary, but has been reported to be as large as 18x on
systems with many virtual interfaces.

Fact gathering subsets
----------------------

It is also possible to configure which subsets of facts are gathered, via
``kolla_ansible_setup_gather_subset``, which is used as the ``gather_subset``
argument to the ``setup`` module. For example, if one wants to avoid collecting
facts via facter:

.. code-block:: yaml

   kolla_ansible_setup_gather_subset: "all,!facter"
