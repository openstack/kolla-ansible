..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

..
 This template should be in ReSTructured text. The filename in the git
 repository should match the launchpad URL, for example a URL of
 https://blueprints.launchpad.net/kolla/+spec/awesome-thing should be named
 awesome-thing.rst . Please do not delete any of the sections in this
 template. If you have nothing to say for a whole section, just write: None
 For help with syntax, see http://www.sphinx-doc.org/en/stable/rest.html
 To test out your formatting, see http://www.tele3.cz/jbar/rest/rest.html

==================================
Enable TLS for OpenStack endpoints
==================================

https://blueprints.launchpad.net/kolla-ansible/+spec/add-ssl-internal-network

This proposal describes implementation of the internal TLS encryption for
OpenStack services deployed with kolla-ansible, i.e. adding support to make
OpenStack internal and admin endpoints encrypted, as well as encrypting traffic
between HAProxy and OpenStack services. Other services are out of scope of this
document. Also, more workflows (using company CA, using certificates already
provisioned on the hosts) are out of the scope, and shall be discussed separately.

Problem description
===================

Kolla-ansible can only enable TLS encryption on the external OpenStack
endpoints, and both internal and admin endpoints are unencrypted, leaving
inter-service communication unsecured. However, some deployments may require an
end-to-end encryption for all the traffic, which is currently not possible.


Use cases
---------
1. There is an external requirement for the deployment to support end-to-end
   encryption of passwords, or all traffic.

Proposed change
===============

This spec proposes extending the encryption to internal TLS traffic between
services by allowing operator to provide a separate set of HAProxy
certificates, that can be used to enable HTTPS encryption on the internal and
admin endpoints, as well as encrypting backend traffic from HAProxy to
OpenStack services. Optionally, a support for self-signed certificates can be
extended, so that deployment can be done without certificates signed by a
trusted CA, while still validating the backend connections.

Security impact
---------------

Implementing this spec will allow operators to deploy OpenStack with end-to-end
encryption of the control plane, preventing exposure of passwords and tokens.

Performance Impact
------------------

Enabling TLS for all inter-service communication will have a small but
measurable impact, due to the requirements for the TLS handshake for each API
call. It's not clear whether OpenStack services can be configured to keep their
HTTP sessions alive, lowering the impact of that change.

Alternatives
------------

An alternate approach has been suggested [1]_, where HAProxy terminates all TLS
traffic, and then either speaks to the localhost backend over unencrypted
connection, or proxies the request to another HAProxy if the local backend is
down. However, the concern has been raised that this approach would not be
enough to satisfy requirements of some operators. Additionally, the
implementation proposed by this document seems more in line with how backend
TLS is implemented by other deployment methods like openstack-ansible [2]_.

.. [1] https://review.opendev.org/#/c/548407/
.. [2] https://docs.openstack.org/openstack-ansible-haproxy_server/pike/configure-haproxy.html, search for `haproxy_backend_ssl`

Implementation
==============

Assignee(s)
-----------

[TBD]

Milestones
----------

[TBD]

Work Items
----------

1. Implement frontend encryption for internal and admin endpoints:
   - Allow for distinct internal and external certificates
   - Add support for merging public and internal/admin networks by reusing
     same endpoints.
   - Support existing deployments by setting correct defaults that behave as
     in stein.
2. Implement per-service backend TLS encryption
   - Introduce per-service ansible variables to control backend TLS encryption
   - Pass the variable to the HAProxy template via the haproxy data structure
     in service's defaults/main.yaml
   - based on the variable generate backend configuration with/without
     encryption.
3. Add support for using self-signed/untrusted certificates both for frontend
   and backend connections. 
   - Change all authorization configs to add `insecure` parameter, which optionally
     disables certificate verification.
   - Ensure that all tasks that interact with OpenStack APIs support disabling
     certificate verification.
   - Fix heat-api bootstrap process, which currently requires valid certificate,
     probably by moving domain/user creation out of the container, and into the
     ansible itself.
   - Allow for providing a CA used to verify connections to the service backends.
   - Change the process of generating self-signed certificates to use a single
     CA for both external and internal connections, and use that CA for
     validating backends.

Testing
=======

A new test scenario will be implemented that does the deployment with internal
and external TLS enabled, running the same set of tests as now, but over
encrypted connection.

Documentation Impact
====================

Documentation has to be expanded, describing TLS requirements for the internal
certificate, as well as all ansible variables used to configure TLS settings
for the deployment.

References
==========
None
