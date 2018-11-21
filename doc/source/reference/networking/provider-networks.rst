.. _provider-networks:

=================
Provider Networks
=================

Provider networks allow to connect compute instances directly to physical
networks avoiding tunnels. This is necessary for example for some performance
critical applications. Only administrators of OpenStack can create such
networks. For provider networks compute hosts must have external bridge
created and configured by Ansible tasks like it is already done for tenant
DVR mode networking. Normal tenant non-DVR networking does not need external
bridge on compute hosts and therefore operators don't need additional
dedicated network interface.

To enable provider networks, modify the ``/etc/kolla/globals.yml`` file
as the following example shows:

.. code-block:: yaml

   enable_neutron_provider_networks: "yes"
