.. _skydive-guide:

================
Skydive in Kolla
================

Overview
~~~~~~~~
Skydive is an open source real-time network topology and protocols analyzer.
It aims to provide a comprehensive way of understanding what is happening in
the network infrastructure.
Skydive agents collect topology information and flows and forward them to a
central agent for further analysis.
All the information is stored in an Elasticsearch database.

Configuration on Kolla deployment
---------------------------------

Enable Skydive in ``/etc/kolla/globals.yml`` file:

.. code-block:: yaml

   enable_skydive: "yes"
   enable_elasticsearch: "yes"

.. end

Verify operation
----------------

After successful deployment, Skydive can be accessed using a browser on
``<kolla_external_vip_address>:8085``.

The default username is ``admin``, the password can be located under
``<keystone_admin_password>`` in ``/etc/kolla/passwords.yml``.

For more information about how Skydive works, see
`Skydive – An open source real-time network topology and protocols analyzer
<https://github.com/skydive-project/skydive/>`__.
