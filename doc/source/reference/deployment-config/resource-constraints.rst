.. _resource-constraints:

====================
Resource Constraints
====================

Overview
~~~~~~~~

Since the Rocky release it is possible to restrict
the resource usage of deployed containers. In Kolla Ansible,
container resources to be constrained are referred to as dimensions.

The `Docker documentation <https://docs.docker.com/config/containers/resource_constraints/>`__
provides information on container resource constraints.
The resources currently supported by Kolla Ansible are:

.. code-block:: console

    cpu_period
    cpu_quota
    cpu_shares
    cpuset_cpus
    cpuset_mems
    mem_limit
    mem_reservation
    memswap_limit
    kernel_memory
    blkio_weight
    ulimits

Pre-deployment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dimensions are defined as a mapping from a Docker resource name

.. list-table:: Resource Constraints
   :widths: 25 25 25
   :header-rows: 1

   * - Resource
     - Data Type
     - Default Value
   * - cpu_period
     - Integer
     - 0
   * - blkio_weight
     - Integer
     - 0
   * - cpu_quota
     - Integer
     - 0
   * - cpu_shares
     - Integer
     - 0
   * - mem_limit
     - Integer
     - 0
   * - memswap_limit
     - Integer
     - 0
   * - mem_reservation
     - Integer
     - 0
   * - cpuset_cpus
     - String
     - ''(Empty String)
   * - cpuset_mems
     - String
     - ''(Empty String)
   * - ulimits
     - Dict
     - {}


The variable ``default_container_dimensions`` sets the default dimensions
for all supported containers, and by default these are unconstrained.

Each supported container has an associated variable,
``<container name>_dimensions``, that can be used to set the resources
for the container. For example, dimensions for the ``nova_libvirt``
container are set via the variable ``nova_libvirt_dimensions``.

For example,
to constrain the number of CPUs that may be used by all supported containers,
add the following to the dimensions options section in
``/etc/kolla/globals.yml``:

.. code-block:: yaml

   default_container_dimensions:
     cpuset_cpus: "1"

For example, to constrain the number of CPUs that may be used by
the ``nova_libvirt`` container, add the following to the dimensions
options section in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   nova_libvirt_dimensions:
     cpuset_cpus: "2"

How to config ulimits in kolla
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

  <container_name>_dimensions:
    ulimits:
      nofile:
        soft: 131072
        hard: 131072
      fsize:
        soft: 131072
        hard: 131072

A list of valid names can be found [here]
(https://github.com/docker/go-units/blob/d4a9b9617350c034730bc5051c605919943080bf/ulimit.go#L46-L63)

Deployment
~~~~~~~~~~

To deploy resource constrained containers, run the deployment as usual:

.. code-block:: console

  $ kolla-ansible deploy -i /path/to/inventory

