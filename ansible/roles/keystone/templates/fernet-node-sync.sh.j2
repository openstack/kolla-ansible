#!/bin/bash

set -o errexit
set -o pipefail

if [ ! -z "$1" ] && [ "$1" == "--check" ]; then
    if [ -f /etc/keystone/fernet-keys/0 ]; then
        if [[ $(stat -c %U:%G /etc/keystone/fernet-keys/0) != "keystone:keystone" ]]; then
            exit 1
        fi
    else
        exit 1
    fi
else
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
fi
