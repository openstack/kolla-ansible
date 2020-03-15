#!/bin/bash

# Check for CRITICAL, ERROR or WARNING messages in log files.

set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function check_file_for_level {
    # $1: file
    # $2: log level
    # Filter out false positives from logged config options.
    sudo egrep " $2 " $1 | egrep -v "(logging_exception_prefix|rate_limit_except_level)"
}

function filter_out_expected_critical {
    # $1: file
    # Filter out expected critical log messages that we do not want to fail the
    # job.

    case $1 in
    */placement-api.log)
        # Sometimes we see this during upgrade when keystone is down.
        grep -v "Failed to fetch token data from identity server"
        ;;
    */neutron-server.log)
        # Sometimes we see this during shutdown (upgrade).
        # See: https://bugs.launchpad.net/neutron/+bug/1863579
        grep -v "WSREP has not yet prepared node for application use"
        ;;
    *)
        # We have to provide some pass-through consumer to avoid:
        #   grep: write error: Broken pipe
        # from check_file_for_level
        cat
        ;;
    esac
}

any_critical=0
for level in CRITICAL ERROR WARNING; do
    all_file=/tmp/logs/kolla/all-${level}.log
    # remove the file to avoid collecting duplicates (upgrade, post)
    rm -f $all_file
    any_matched=0
    echo "Checking for $level log messages"
    for f in $(sudo find /var/log/kolla/ -type f); do
        if check_file_for_level $f $level >/dev/null; then
            any_matched=1
            if [[ $level = CRITICAL ]]; then
                if check_file_for_level $f $level | filter_out_expected_critical $f >/dev/null; then
                    any_critical=1
                fi
            fi
            echo $f >> $all_file
            check_file_for_level $f $level >> $all_file
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
