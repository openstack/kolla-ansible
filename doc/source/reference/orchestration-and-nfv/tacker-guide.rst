==========================
Tacker - NFV orchestration
==========================

"Tacker is an OpenStack service for NFV Orchestration with a general purpose
VNF Manager to deploy and operate Virtual Network Functions (VNFs) and
Network Services on an NFV Platform. It is based on ETSI MANO Architectural
Framework."
For more details about Tacker, see `OpenStack Tacker Documentation
<https://docs.openstack.org/tacker/latest/>`__.

Overview
~~~~~~~~

As of the Pike release, tacker requires the following services
to be enabled to operate correctly.

* Core compute stack (nova, neutron, glance, etc)
* Heat
* Mistral + Redis
* Barbican (Required only for multinode)

Optionally tacker supports the following services and features.

* Aodh
* Ceilometer
* Networking-sfc
* Opendaylight

Compatibility
~~~~~~~~~~~~~

Tacker is supported by the following distros and install_types.

* Centos, Redhat and Oraclelinux.

  * Source and binary images.

* Debian and Ubuntu.

  * Only source images.

Preparation and Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~

By default tacker and required services are disabled in
the ``group_vars/all.yml`` file.
In order to enable them, you need to edit the file
``/etc/kolla/globals.yml`` and set the following variables:

.. note::

   Heat is enabled by default, ensure it is not disabled.

.. code-block:: yaml

   enable_tacker: "yes"
   enable_barbican: "yes"
   enable_mistral: "yes"
   enable_redis: "yes"

.. warning::

   Barbican is required in multinode deployments to share VIM fernet_keys.
   If not enabled, only one tacker-server host will have the keys on it
   and any request made to a different tacker-server will fail with a
   similar error as ``No such file or directory /etc/tacker/vim/fernet_keys``

Deploy tacker and related services.

.. code-block:: console

   $ kolla-ansible deploy

Verification
~~~~~~~~~~~~

Generate the credentials file.

.. code-block:: console

   $ kolla-ansible post-deploy

Source credentials file.

.. code-block:: console

   $ . /etc/kolla/admin-openrc.sh

Create base neutron networks and glance images.

.. code-block:: console

   $ ./tools/init-runonce

.. note::

   ``init-runonce`` file is located in ``$PYTHON_PATH/kolla-ansible``
   folder in kolla-ansible installation from pip.

In kolla-ansible git repository a `tacker demo <https://github.com/openstack/kolla-ansible/tree/master/contrib/demos/tacker>`_
is present in ``kolla-ansible/contrib/demos/tacker/`` that will
create a very basic VNF from a cirros image in ``demo-net`` network.

Install python-tackerclient.

.. note::

   Barbican, heat and mistral python clients are in tacker's
   requirements and will be installed as dependency.

.. code-block:: console

   $ pip install python-tackerclient

Execute ``deploy-tacker-demo`` script to initialize the VNF creation.

.. code-block:: console

   $ ./deploy-tacker-demo

Tacker demo script will create sample VNF Descriptor (VNFD) file,
then register a default VIM, create a tacker VNFD and finally
deploy a VNF from the previously created VNFD.


After a few minutes, the tacker VNF is ACTIVE with a cirros instance
running in nova and with its corresponding heat stack CREATION_COMPLETE.

Verify tacker VNF status is ACTIVE.

.. code-block:: console

   $ openstack vnf list

   +--------------------------------------+------------------+-----------------------+--------+--------------------------------------+--------------------------------------+
   | ID                                   | Name             | Mgmt Url              | Status | VIM ID                               | VNFD ID                              |
   +--------------------------------------+------------------+-----------------------+--------+--------------------------------------+--------------------------------------+
   | c52fcf99-101d-427b-8a2d-c9ef54af8b1d | kolla-sample-vnf | {"VDU1": "10.0.0.10"} | ACTIVE | eb3aa497-192c-4557-a9d7-1dff6874a8e6 | 27e8ea98-f1ff-4a40-a45c-e829e53b3c41 |
   +--------------------------------------+------------------+-----------------------+--------+--------------------------------------+--------------------------------------+

Verify nova instance status is ACTIVE.

.. code-block:: console

   $ openstack server list

   +--------------------------------------+-------------------------------------------------------+--------+--------------------+--------+-----------------------------------------------------------------------------------------------------------------------+
   | ID                                   | Name                                                  | Status | Networks           | Image  | Flavor                                                                                                                |
   +--------------------------------------+-------------------------------------------------------+--------+--------------------+--------+-----------------------------------------------------------------------------------------------------------------------+
   | d2d59eeb-8526-4826-8f1b-c50b571395e2 | ta-cf99-101d-427b-8a2d-c9ef54af8b1d-VDU1-fchiv6saay7p | ACTIVE | demo-net=10.0.0.10 | cirros | tacker.vnfm.infra_drivers.openstack.openstack_OpenStack-c52fcf99-101d-427b-8a2d-c9ef54af8b1d-VDU1_flavor-yl4bzskwxdkn |
   +--------------------------------------+-------------------------------------------------------+--------+--------------------+--------+-----------------------------------------------------------------------------------------------------------------------+

Verify Heat stack status is CREATE_COMPLETE.

.. code-block:: console

   $ openstack stack list

   +--------------------------------------+----------------------------------------------------------------------------------------------+----------------------------------+-----------------+----------------------+--------------+
   | ID                                   | Stack Name                                                                                   | Project                          | Stack Status    | Creation Time        | Updated Time |
   +--------------------------------------+----------------------------------------------------------------------------------------------+----------------------------------+-----------------+----------------------+--------------+
   | 289a6686-70f6-4db7-aa10-ed169fe547a6 | tacker.vnfm.infra_drivers.openstack.openstack_OpenStack-c52fcf99-101d-427b-8a2d-c9ef54af8b1d | 1243948e59054aab83dbf2803e109b3f | CREATE_COMPLETE | 2017-08-23T09:49:50Z | None         |
   +--------------------------------------+----------------------------------------------------------------------------------------------+----------------------------------+-----------------+----------------------+--------------+

After the correct functionality of tacker is verified, tacker demo
can be cleaned up executing ``cleanup-tacker`` script.

.. code-block:: console

   $ ./cleanup-tacker

