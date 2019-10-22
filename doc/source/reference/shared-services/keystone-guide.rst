.. _keystone-guide:

===========================
Keystone - Identity service
===========================

Tokens
------

The Keystone token provider is configured via ``keystone_token_provider``. The
default value for this is ``fernet``.

Fernet Tokens
~~~~~~~~~~~~~

Fernet tokens require the use of keys that must be synchronised between
Keystone servers. Kolla Ansible deploys two containers to handle this -
``keystone_fernet`` runs cron jobs to rotate keys via rsync when necessary.
``keystone_ssh`` is an SSH server that provides the transport for rsync. In a
multi-host control plane, these rotations are performed by the hosts in a
round-robin manner.

The following variables may be used to configure the token expiry and key
rotation.

``fernet_token_expiry``
    Keystone fernet token expiry in seconds. Default is 86400, which is 1 day.
``fernet_token_allow_expired_window``
    Keystone window to allow expired fernet tokens. Default is 172800, which is
    2 days.
``fernet_key_rotation_interval``
    Keystone fernet key rotation interval in seconds. Default is sum of token
    expiry and allow expired window, which is 3 days.

The default rotation interval is set up to ensure that the minimum number of
keys may be active at any time. This is one primary key, one secondary key and
a buffer key - three in total. If the rotation interval is set lower than the
sum of the token expiry and token allow expired window, more active keys will
be configured in Keystone as necessary.

Further infomation on Fernet tokens is available in the :keystone-doc:`Keystone
documentation <admin/fernet-token-faq.html>`.
