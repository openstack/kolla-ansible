A Kolla Demo using Tacker
=========================

By default, the deploy script will spawn 1 Nova instance on a Neutron
network created from the tools/init-runonce script.

Then run the deploy script:

::

    $ ./deploy-tacker-demo

After the demo is deployed, a cleanup script can be used to remove
resources created by deploy script.

To run the cleanup script:

::

    $ ./cleanup-tacker
