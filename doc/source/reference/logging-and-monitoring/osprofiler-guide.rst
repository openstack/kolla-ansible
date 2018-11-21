.. _osprofiler-guide:

====================================
OSprofiler - Cross-project profiling
====================================

Overview
~~~~~~~~

OSProfiler provides a tiny but powerful library that is used by most
(soon to be all) OpenStack projects and their corresponding python clients
as well as the Openstack client.
It provides functionality to generate 1 trace per request, that goes
through all involved services. This trace can then be extracted and used
to build a tree of calls which can be quite handy for a variety of reasons
(for example in isolating cross-project performance issues).

Configuration on Kolla deployment
---------------------------------

Enable ``OSprofiler`` in ``/etc/kolla/globals.yml`` file:

.. code-block:: yaml

   enable_osprofiler: "yes"
   enable_elasticsearch: "yes"

Verify operation
----------------

Retrieve ``osprofiler_secret`` key present at ``/etc/kolla/passwords.yml``.

Profiler UUIDs can be created executing OpenStack clients (Nova, Glance,
Cinder, Heat, Keystone) with ``--profile`` option or using the official
Openstack client with ``--os-profile``. In example to get the OSprofiler trace
UUID for :command:`openstack server create` command.

.. code-block:: console

   $ openstack --os-profile <OSPROFILER_SECRET> server create \
     --image cirros --flavor m1.tiny --key-name mykey \
     --nic net-id=${NETWORK_ID} demo

The previous command will output the command to retrieve OSprofiler trace.

.. code-block:: console

   $ osprofiler trace show --html <TRACE_ID> --connection-string \
     elasticsearch://<api_interface_address>:9200

For more information about how OSprofiler works, see
`OSProfiler – Cross-project profiling library
<https://docs.openstack.org/osprofiler/latest/>`__.
