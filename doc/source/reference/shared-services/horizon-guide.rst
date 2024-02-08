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
a file named _9999-custom-settings.py should be created under the directory
``{{ node_custom_config }}/horizon/`` with the following contents:

.. code-block:: python

   AVAILABLE_THEMES = [
                ('material', 'Material', 'themes/material'),
   ]

As a result material theme will be the only one available, and used by default.
Other way of setting default theme is shown in the next section.

Adding custom themes
--------------------

It is possible to add custom themes to be available for Horizon
by using ``horizon_custom_themes`` configuration variable in ``globals.yml``.
This entry updates AVAILABLE_THEMES adding the new theme at the list end.

.. code-block:: yaml

   horizon_custom_themes:
     - name: my_custom_theme
       label: CustomTheme

Theme files have to be copied into:
``{{ node_custom_config }}/horizon/themes/my_custom_theme``.
The new theme can be set as default in _9999-custom-settings.py:

.. code-block:: python

   DEFAULT_THEME = 'my_custom_theme'

