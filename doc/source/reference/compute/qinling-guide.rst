.. _qinling-guide:

=========================
Qinling - Function Engine
=========================

Overview
~~~~~~~~

Qinling aims to provide a platform to support serverless functions
(like AWS Lambda). Qinling supports different container orchestration
platforms (Kubernetes/Swarm, etc...) and different function package storage
backends (local/Swift/S3) by nature using plugin mechanism.

Kolla deploys Qinling API and Qinling Engine containers which are the main
Qinling components but it needs to be connected to an existing container
orchestration platforms.

Apply custom policies to Qinling API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Custom policies could be apply by creating ``policy.json`` file under
``/etc/kolla/config/qinling`` directory.

Enable etcd role
~~~~~~~~~~~~~~~~

Qinling requires etcd for function mapping and concurrency. The etcd role
should be enabled to configure the etcd address and port within `qinling.conf`.

Look for ``enable_etcd: "no"`` and change it in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   enable_etcd: "yes"

Connect to an existing Kubernetes cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Certificates
------------

``qinling-engine`` authenticates to Kubernetes by using certificates.

.. note::
   If the cluster has not been created with OpenStack Magnum then
   certificates need to be gathered using different methods that will not
   be mentioned here.

If the Kubernetes cluster has been deployed with OpenStack Magnum then the
OpenStack client should be used to retrieve the certificates.

.. code-block:: console

   openstack coe cluster config --dir . 687f7476-5604-4b44-8b09-b7a4f3fdbd64 --output-certs

Where ``687f7476-5604-4b44-8b09-b7a4f3fdbd64`` is the Kubernetes cluster ID
created with Magnum.

Four files should have been generated:

* ``ca.pem``
* ``cert.pem``
* ``key.pem``
* ``config``

Only ``ca.pem``, ``cert.pem`` and ``key.pem`` will be used, these files have
to be stored in ``/etc/kolla/config/qinling/qinling-engine`` directory under
these file name:

* ``ca.pem``: ``/etc/kolla/config/qinling/qinling-engine/kubernetes_ca.crt``
* ``cert.pem``: ``/etc/kolla/config/qinling/qinling-engine/kubernetes.crt``
* ``key.pem``: ``/etc/kolla/config/qinling/qinling-engine/kubernetes.key``


Declare ``qinling_kubernetes_certificates`` variable in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   qinling_kubernetes_certificates: "yes"

Kubernetes cluster
------------------

``qinling-engine`` needs to know where to connect, the information is
provided by options under ``[kubernetes]`` section inside ``qinling.conf``
configuration file.

As mentioned above, these settings are only required by ``qinling-engine``,
put the content in ``/etc/kolla/config/qinling/qinling-engine.conf``.

.. code-block:: ini

   [kubernetes]
   kube_host = https://192.168.1.168:6443
   ssl_ca_cert = /etc/qinling/pki/kubernetes/ca.crt
   cert_file = /etc/qinling/pki/kubernetes/qinling.crt
   key_file = /etc/qinling/pki/kubernetes/qinling.key

``kube_host`` is the Kubernetes cluster API address, ``https`` protocol
has to be defined.
