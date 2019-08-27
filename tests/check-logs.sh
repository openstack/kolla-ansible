#!/bin/bash

# Check for CRITICAL, ERROR or WARNING messages in log files.

set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


for level in CRITICAL ERROR WARNING; do
    all_file=/tmp/logs/kolla/all-${level}.log
    any_matched=0
    any_critical=0
    echo "Checking for $level log messages"
    for f in $(sudo find /var/log/kolla/ -type f); do
        if sudo egrep "^.* .* .* $level" $f >/dev/null; then
            any_matched=1
            if [[ $level = CRITICAL ]]; then
                any_critical=1
            fi
            echo $f >> $all_file
            sudo egrep "^.* .* .* $level" $f >> $all_file
            echo >> $all_file
        fi
    done
    if [[ $any_matched -eq 1 ]]; then
        echo "Found some $level log messages. Matches in $all_file"
    fi
done

if [[ $any_critical -eq 1 ]]; then
    echo "Found critical log messages - failing job."
    exit 1
fi
