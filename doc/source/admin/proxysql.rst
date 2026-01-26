========
ProxySQL
========

ProxySQL provides loadbalancing to MariaDB. Prior to 2025.1 release,
HAProxy was the default loadbalancer for database like other services.
But from 2025.1, the ProxySQL became the default and the support for
HAProxy as a database loadbalancer will be discontinued from 2025.2.

.. note::

  If your MariaDB cluster is not managed by Kolla-Ansible, this is
  not applied.

Migrating from HAProxy
~~~~~~~~~~~~~~~~~~~~~~

The migration is automatically handled by Kolla-Ansible. By default,
ProxySQL gets enabled when MariaDB is enabled from 2025.1 release.
So, if users are coming from 2024.1 or 2024.2 release, they can
simply run service upgrade command.

Upgrading ProxySQL from 2.7.x to 3.0.x
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default version of ProxySQL for 2025.1 release is 2.7.x however
this version of ProxySQL has a bug that it does not send all
certificate chain during SSL handshake. See `ProxySQL issue 4877
<https://github.com/sysown/proxysql/issues/4877>`__ for more detail.
This bug was fixed on ProxySQL 3.0.x but not in 2.7.x release.

This bug does not affect users system unless they use chain of
certificates for database TLS (e.g. Use of intermediate certificate)
If however, this does affect your system, you can upgrade your ProxySQL
by following.

1. Set ``proxysql_version`` to 3

  .. code-block:: yaml

    proxysql_version: 3

2. Run service deployment for loadbalancers

  .. code-block:: bash

    $ kolla-ansible deploy -i <inventory> -t loadbalancer

3. Verify the version of ProxySQL after deployment

  .. code-block:: bash

    $ docker exec proxysql proxysql --version
    $ ProxySQL version 3.0.5
