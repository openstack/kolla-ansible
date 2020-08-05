#!/bin/bash

set -o errexit
set -o pipefail

# Ensure tokens are populated, check for 0 key which should always exist
n=0
while [ ! -f /etc/keystone/fernet-keys/0 ]; do
    if [ $n -lt 10 ]; then
        n=$(( n + 1 ))
        echo "ERROR: Fernet tokens have not been populated, rechecking in 1 minute"
        echo "DEBUG: /etc/keystone/fernet-keys contents:"
        ls -l /etc/keystone/fernet-keys/
        sleep 60
    else
        echo "CRITICAL: Waited for 10 minutes - failing"
        exit 1
    fi
done
