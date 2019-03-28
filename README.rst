========================
Team and repository tags
========================

.. image:: https://governance.openstack.org/tc/badges/kolla-ansible.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. Change things from this point on

======================
Kolla-Ansible Overview
======================

The Kolla-Ansible is a deliverable project separated from Kolla project.

Kolla-Ansible deploys OpenStack services and infrastructure components
in Docker containers.

Kolla's mission statement is:

::

    To provide production-ready containers and deployment tools for operating
    OpenStack clouds.

Kolla is highly opinionated out of the box, but allows for complete
customization. This permits operators with little experience to deploy
OpenStack quickly and as experience grows modify the OpenStack
configuration to suit the operator's exact requirements.

Getting Started
===============

Learn about Kolla-Ansible by reading the documentation online
`Kolla-Ansible <https://docs.openstack.org/kolla-ansible/latest/>`__.

Get started by reading the `Developer
Quickstart <https://docs.openstack.org/kolla-ansible/latest/user/quickstart.html>`__.

OpenStack services
------------------

Kolla-Ansible deploys containers for the following OpenStack projects:

- `Aodh <https://docs.openstack.org/aodh/latest/>`__
- `Barbican <https://docs.openstack.org/barbican/latest/>`__
- `Bifrost <https://docs.openstack.org/bifrost/latest/>`__
- `Blazar <https://docs.openstack.org/blazar/latest/>`__
- `Ceilometer <https://docs.openstack.org/ceilometer/latest/>`__
- `Cinder <https://docs.openstack.org/cinder/latest/>`__
- `CloudKitty <https://docs.openstack.org/cloudkitty/latest/>`__
- `Congress <https://docs.openstack.org/congress/latest/>`__
- `Cyborg <https://docs.openstack.org/cyborg/latest/>`__
- `Designate <https://docs.openstack.org/designate/latest/>`__
- `Freezer <https://docs.openstack.org/freezer/latest/>`__
- `Glance <https://docs.openstack.org/glance/latest/>`__
- `Heat <https://docs.openstack.org/heat/latest/>`__
- `Horizon <https://docs.openstack.org/horizon/latest/>`__
- `Ironic <https://docs.openstack.org/ironic/latest/>`__
- `Karbor <https://docs.openstack.org/karbor/latest/>`__
- `Keystone <https://docs.openstack.org/keystone/latest/>`__
- `Kuryr <https://docs.openstack.org/kuryr/latest/>`__
- `Magnum <https://docs.openstack.org/magnum/latest/>`__
- `Manila <https://docs.openstack.org/manila/latest/>`__
- `Mistral <https://docs.openstack.org/mistral/latest/>`__
- `Monasca <https://docs.openstack.org/monasca-api/latest/>`__
- `Murano <https://docs.openstack.org/murano/latest/>`__
- `Neutron <https://docs.openstack.org/neutron/latest/>`__
- `Nova <https://docs.openstack.org/nova/latest/>`__
- `Octavia <https://docs.openstack.org/octavia/latest/>`__
- `Panko <https://docs.openstack.org/panko/latest/>`__
- `Rally <https://docs.openstack.org/rally/latest/>`__
- `Sahara <https://docs.openstack.org/sahara/latest/>`__
- `Searchlight <https://docs.openstack.org/searchlight/latest/>`__
- `Senlin <https://docs.openstack.org/senlin/latest/>`__
- `Solum <https://docs.openstack.org/solum/latest/>`__
- `Swift <https://docs.openstack.org/swift/latest/>`__
- `Tacker <https://docs.openstack.org/tacker/latest/>`__
- `Tempest <https://docs.openstack.org/tempest/latest/>`__
- `Trove <https://docs.openstack.org/trove/latest/>`__
- `Vitrage <https://docs.openstack.org/vitrage/latest/>`__
- `Vmtp <https://vmtp.readthedocs.io/en/latest/>`__
- `Watcher <https://docs.openstack.org/watcher/latest/>`__
- `Zun <https://docs.openstack.org/zun/latest/>`__

Infrastructure components
-------------------------

Kolla-Ansible deploys containers for the following infrastructure components:

- `Ceph <https://ceph.com/>`__ implementation for Cinder, Glance and Nova.
- `Collectd <https://collectd.org/>`__,
  `Telegraf <https://docs.influxdata.com/telegraf/>`__,
  `InfluxDB <https://influxdata.com/time-series-platform/influxdb/>`__,
  `Prometheus <https://prometheus.io/>`__, and
  `Grafana <https://grafana.org/>`__ for performance monitoring.
- `Elasticsearch <https://www.elastic.co/de/products/elasticsearch/>`__ and
  `Kibana <https://www.elastic.co/de/products/kibana/>`__ to search, analyze,
  and visualize log messages.
- `Etcd <https://coreos.com/etcd/>`__ a distributed reliable key-value store.
- `Fluentd <https://www.fluentd.org/>`__ as an open source data collector
  for unified logging layer.
- `Gnocchi <https://gnocchi.xyz/>`__ A time-series storage database.
- `HAProxy <https://www.haproxy.org/>`__ and
  `Keepalived <http://www.keepalived.org/>`__ for high availability of services
  and their endpoints.
- `MariaDB and Galera Cluster <https://mariadb.com/kb/en/mariadb/galera-cluster/>`__
  for highly available MySQL databases.
- `Memcached <https://memcached.org/>`__ a distributed memory object caching system.
- `MongoDB <https://www.mongodb.org/>`__ as a database back end for Panko.
- `Open vSwitch <http://openvswitch.org/>`__ and Linuxbridge backends for Neutron.
- `RabbitMQ <https://www.rabbitmq.com/>`__ as a messaging backend for
  communication between services.
- `Redis <https://redis.io/>`__ an in-memory data structure store.
- `Zookeeper <https://zookeeper.apache.org/>`__ an open-source server which enables
  highly reliable distributed coordination.

Directories
===========

-  ``ansible`` - Contains Ansible playbooks to deploy OpenStack services and
   infrastructure components in Docker containers.
-  ``contrib`` - Contains demos scenarios for Heat, Magnum and Tacker and a
   development environment for Vagrant
-  ``doc`` - Contains documentation.
-  ``etc`` - Contains a reference etc directory structure which requires
   configuration of a small number of configuration variables to achieve
   a working All-in-One (AIO) deployment.
-  ``kolla_ansible`` - Contains password generation script.
-  ``releasenotes`` - Contains releasenote of all features added in
   Kolla-Ansible.
-  ``specs`` - Contains the Kolla-Ansible communities key arguments about
   architectural shifts in the code base.
-  ``tests`` - Contains functional testing tools.
-  ``tools`` - Contains tools for interacting with Kolla-Ansible.
-  ``zuul.d`` - Contains project gate job definitions.

Getting Involved
================

Need a feature? Find a bug? Let us know! Contributions are much
appreciated and should follow the standard `Gerrit
workflow <https://docs.openstack.org/infra/manual/developers.html>`__.

-  We communicate using the #openstack-kolla irc channel.
-  File bugs, blueprints, track releases, etc on
   `Launchpad <https://launchpad.net/kolla-ansible>`__.
-  Attend weekly
   `meetings <https://wiki.openstack.org/wiki/Meetings/Kolla>`__.
-  Contribute `code <https://git.openstack.org/openstack/kolla-ansible>`__.

Contributors
============

Check out who's `contributing
code <http://stackalytics.com/?module=kolla-group&metric=commits>`__ and
`contributing
reviews <http://stackalytics.com/?module=kolla-group&metric=marks>`__.

Notices
=======

Docker and the Docker logo are trademarks or registered trademarks of
Docker, Inc. in the United States and/or other countries. Docker, Inc.
and other parties may also have trademark rights in other terms used herein.
