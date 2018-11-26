.. nova-fake-driver:

================
Nova Fake Driver
================

One common question from OpenStack operators is that "how does the control
plane (for example, database, messaging queue, nova-scheduler ) scales?".
To answer this question, operators setup Rally to drive workload to the
OpenStack cloud. However, without a large number of nova-compute nodes,
it becomes difficult to exercise the control performance.

Given the built-in feature of Docker container, Kolla enables standing up many
of Compute nodes with nova fake driver on a single host. For example,
we can create 100 nova-compute containers on a real host to simulate the
100-hypervisor workload to the ``nova-conductor`` and the messaging queue.

Use nova-fake driver
~~~~~~~~~~~~~~~~~~~~

Nova fake driver can not work with all-in-one deployment. This is because the
fake ``neutron-openvswitch-agent`` for the fake ``nova-compute`` container
conflicts with ``neutron-openvswitch-agent`` on the Compute nodes. Therefore,
in the inventory the network node must be different than the Compute node.

By default, Kolla uses libvirt driver on the Compute node. To use nova-fake
driver, edit the following parameters in ``/etc/kolla/globals.yml`` or in
the command line options.

.. code-block:: yaml

   enable_nova_fake: "yes"
   num_nova_fake_per_node: 5

Each Compute node will run 5 ``nova-compute`` containers and 5
``neutron-plugin-agent`` containers. When booting instance, there will be
no real instances created. But :command:`nova list` shows the fake instances.
