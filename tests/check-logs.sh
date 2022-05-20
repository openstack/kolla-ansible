#!/bin/bash

# Check for CRITICAL, ERROR or WARNING messages in log files.

set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function check_openstack_log_file_for_level {
    # $1: file
    # $2: log level
    # Filter out false positives from logged config options.
    sudo egrep " $2 " $1 | egrep -v "(logging_exception_prefix|rate_limit_except_level)"
}

function check_fluentd_log_file_for_level {
    # $1: file
    # $2: log level
    sudo egrep "\[$2\]:" $1
}

function filter_out_expected_critical {
    # $1: file
    # Filter out expected critical log messages that we do not want to fail the
    # job.

    case $1 in
    */neutron-server.log)
        # Sometimes we see this during shutdown (upgrade).
        # See: https://bugs.launchpad.net/neutron/+bug/1863579
        grep -v "WSREP has not yet prepared node for application use" |
        grep -v "Failed to fetch token data from identity server"
        ;;
    *)
        # Sometimes we see this during upgrades of Keystone.
        # Usually in Placement but also in Neutron and Nova.
        # Especially in AIO.
        grep -v "Failed to fetch token data from identity server"
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
        if check_openstack_log_file_for_level $f $level >/dev/null; then
            any_matched=1
            if [[ $level = CRITICAL ]]; then
                if check_openstack_log_file_for_level $f $level | filter_out_expected_critical $f >/dev/null; then
                    any_critical=1
                fi
            fi
            echo $f >> $all_file
            check_openstack_log_file_for_level $f $level >> $all_file
            echo >> $all_file
        fi
    done
    if [[ $any_matched -eq 1 ]]; then
        echo "Found some $level log messages. Matches in $all_file"
    fi
done


# check fluentd errors (we consider them critical)
fluentd_log_file=/var/log/kolla/fluentd/fluentd.log
fluentd_error_summary_file=/tmp/logs/kolla/fluentd-error.log
if check_fluentd_log_file_for_level $fluentd_log_file error >/dev/null; then
    any_critical=1
    echo "(critical) Found some error log messages in fluentd logs. Matches in $fluentd_error_summary_file"
    check_fluentd_log_file_for_level $fluentd_log_file error > $fluentd_error_summary_file
    echo >> $fluentd_error_summary_file
fi


if [[ $any_critical -eq 1 ]]; then
    echo "Found critical log messages - failing job."
    exit 1
fi
