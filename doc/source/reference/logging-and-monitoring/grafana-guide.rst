.. _grafana-guide:

=======
Grafana
=======

Overview
~~~~~~~~

`Grafana <https://grafana.com>`_ is open and composable observability and
data visualization platform. Visualize metrics, logs, and traces from
multiple sources like Prometheus, Loki, Elasticsearch,
Postgres and many more..

Preparation and deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~

To enable Grafana, modify the configuration file ``/etc/kolla/globals.yml``
and change the following:

.. code-block:: yaml

   enable_grafana: true

If you would like to set up Prometheus as a data source, additionally set:

.. code-block:: yaml

   enable_prometheus: true

Please follow :doc:`Prometheus Guide <prometheus-guide>` for more information.

LDAP Authentication
~~~~~~~~~~~~~~~~~~~

Grafana can be configured to use LDAP for user authentication. To enable this
feature, set the following variable in ``/etc/kolla/globals.yml``:

.. code-block:: yaml

   grafana_ldap_enabled: true

The configuration for the LDAP server should be provided in a ``ldap.toml``
file placed in the ``{{ node_custom_config }}/grafana/`` folder on the control
host.

Example ``ldap.toml`` configuration:

.. code-block:: ini

   [[servers]]
   host = "openstack.org"
   port = 389
   use_ssl = false
   start_tls = true

   bind_dn = "CN=svc-openstack-grafana,OU=serviceaccounts,DC=openstack,DC=org"
   bind_password = "strong_password"

   search_filter = "(sAMAccountName=%s)"
   search_base_dns = ["OU=Users,DC=openstack,DC=org"]

   [servers.attributes]
   name = "givenName"
   surname = "sn"
   username = "uid"
   member_of = "memberOf"
   email = "mail"

   [[servers.group_mappings]]
   group_dn = "cn=grafana-admins,ou=groups,dc=openstack,dc=org"
   org_role = "Admin"

   [[servers.group_mappings]]
   group_dn = "cn=grafana-editors,ou=groups,dc=openstack,dc=org"
   org_role = "Editor"

   [[servers.group_mappings]]
   group_dn = "*"
   org_role = "Viewer"

Custom dashboards provisioning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kolla Ansible sets custom dashboards provisioning using `Dashboard provider <https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards>`_.

Dashboard JSON files should be placed into the
``{{ node_custom_config }}/grafana/dashboards/`` folder. The use of
sub-folders is also supported when using a custom ``provisioning.yaml``
file. Dashboards will be imported into the Grafana dashboards 'General'
folder by default.

Grafana provisioner config can be altered by placing ``provisioning.yaml`` to
``{{ node_custom_config }}/grafana/`` folder.

For other settings, follow configuration reference:
`Dashboard provider configuration <https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards>`_.
