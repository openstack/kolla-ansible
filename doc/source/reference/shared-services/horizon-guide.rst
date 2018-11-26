.. _horizon-guide:

=============================
Horizon - OpenStack dashboard
=============================

Overview
~~~~~~~~

Kolla can deploy a full working Horizon dashboard setup in either
a **all-in-one** or **multinode** setup.

Extending the default local_settings options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to extend the default configuration options for
Horizon by using a custom python settings file that will override
the default options set on the local_settings file.

As an example, for setting a different (material) theme as the default one,
a file named custom_local_settings should be created under the directory
``{{ node_custom_config }}/horizon/`` with the following contents:

.. code-block:: python

   AVAILABLE_THEMES = [
                ('material', 'Material', 'themes/material'),
   ]

