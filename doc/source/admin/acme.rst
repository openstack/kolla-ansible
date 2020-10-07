.. acme:

==============================
ACME http-01 challenge support
==============================

This guide describes how to configure Kolla Ansible to enable ACME http-01
challenge support.
As of Victoria, Kolla Ansible supports configuring HAProxy Horizon frontend
to proxy ACME http-01 challenge requests to selected external (not deployed
by Kolla Ansible) ACME client servers. These can be ad-hoc or regular servers.
This guide assumes general knowledge of ACME.

Do note ACME supports http-01 challenge only over official HTTP(S) ports, that
is 80 (for HTTP) and 443 (for HTTPS). Only Horizon is normally deployed on such
port with Kolla Ansible (other services use custom ports). This means that,
as of now, running Horizon is mandatory to support ACME http-01 challenge.

How To (External ACME client)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need to determine the IP address (and port) of the ACME client server
used for http-01 challenge (e.g. the host you use to run certbot).
The default port is usually ``80`` (HTTP). Assuming the IP address of that host
is ``192.168.1.1``, the config would look like the following:

.. code-block:: yaml

  enable_horizon: "yes"
  acme_client_servers:
    - server certbot 192.168.1.1:80

``acme_client_servers`` is a list of HAProxy backend server directives. The
first parameter is the name of the backend server - it can be arbitrary and
is used for logging purposes.

After (re)deploying, you can proceed with running the client to host the
http-01 challenge files. Please ensure Horizon frontend responds on the domain
you request the certificate for.

To use the newly-generated key-cert pair, follow the :doc:`tls` guide.
