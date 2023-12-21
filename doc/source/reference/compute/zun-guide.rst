=======================
Zun - Container service
=======================

"Zun is an OpenStack Container service. It aims to provide an
OpenStack API for provisioning and managing containerized
workload on OpenStack."
For more details about Zun, see `OpenStack Zun Documentation
<https://docs.openstack.org/zun/latest/>`__.

Preparation and Deployment
--------------------------

By default Zun and its dependencies are disabled.
In order to enable Zun, you need to edit globals.yml and set the
following variables:

.. code-block:: yaml

   enable_zun: "yes"
   enable_kuryr: "yes"
   enable_etcd: "yes"
   docker_configure_for_zun: "yes"
   containerd_configure_for_zun: "yes"

Docker reconfiguration requires rebootstrapping before deploy.
Make sure you understand the consequences of restarting Docker.
Please see :ref:`rebootstrapping` for details.
If it's initial deploy, then there is nothing to worry about
because it's initial bootstrapping as well and there are no
running services to affect.

.. code-block:: console

   $ kolla-ansible bootstrap-servers

Finally deploy:

.. code-block:: console

   $ kolla-ansible deploy

Verification
------------

#. Generate the credentials file:

   .. code-block:: console

      $ kolla-ansible post-deploy

#. Source credentials file:

   .. code-block:: console

      $ . /etc/kolla/admin-openrc.sh

#. Download and create a glance container image:

   .. code-block:: console

      $ docker pull cirros
      $ docker save cirros | openstack image create cirros --public \
        --container-format docker --disk-format raw

#. Create zun container:

   .. code-block:: console

      $ zun create --name test --net network=demo-net cirros ping -c4 8.8.8.8

   .. note::

      Kuryr does not support networks with DHCP enabled, disable DHCP in the
      subnet used for zun containers.

      .. code-block:: console

         $ openstack subnet set --no-dhcp <subnet>

#. Verify container is created:

   .. code-block:: console

      $ zun list

      +--------------------------------------+------+---------------+---------+------------+------------+-------+
      | uuid                                 | name | image         | status  | task_state | addresses  | ports |
      +--------------------------------------+------+---------------+---------+------------+------------+-------+
      | 3719a73e-5f86-47e1-bc5f-f4074fc749f2 | test | cirros        | Created | None       | 172.17.0.3 | []    |
      +--------------------------------------+------+---------------+---------+------------+------------+-------+

#. Start container:

   .. code-block:: console

      $ zun start test
      Request to start container test has been accepted.

#. Verify container:

   .. code-block:: console

      $ zun logs test
      PING 8.8.8.8 (8.8.8.8): 56 data bytes
      64 bytes from 8.8.8.8: seq=0 ttl=45 time=96.396 ms
      64 bytes from 8.8.8.8: seq=1 ttl=45 time=96.504 ms
      64 bytes from 8.8.8.8: seq=2 ttl=45 time=96.721 ms
      64 bytes from 8.8.8.8: seq=3 ttl=45 time=95.884 ms

      --- 8.8.8.8 ping statistics ---
      4 packets transmitted, 4 packets received, 0% packet loss
      round-trip min/avg/max = 95.884/96.376/96.721 ms

For more information about how zun works, see
`zun, OpenStack Container service <https://docs.openstack.org/zun/latest/>`__.
