#!/bin/bash -x

# We need to run haproxy with one `-f` for each service, because including an
# entire config directory was not a feature until version 1.7 of HAProxy.
# So, append "-f $cfg" to the haproxy command for each service file.
# This will run haproxy_cmd *exactly once*.
find /etc/haproxy/services.d/ -mindepth 1 -print0 | \
    xargs -0 -Icfg echo -f cfg | \
    xargs /usr/sbin/haproxy -W -db -p /run/haproxy.pid -f /etc/haproxy/haproxy.cfg
