#!/bin/bash

set -o xtrace
set -o errexit
set -o nounset
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function mariadb_stop {
    echo "Stopping the database cluster"
    kolla-ansible stop -i ${RAW_INVENTORY} -vvv --yes-i-really-really-mean-it --tags mariadb --skip-tags common
    if [[ $(sudo ${container_engine} ps -q | grep mariadb | wc -l) -ne 0 ]]; then
        echo "Failed to stop MariaDB cluster"
        return 1
    fi
}

function mariadb_recovery {
    # Recover the database cluster.
    echo "Recovering the database cluster"
    kolla-ansible mariadb-recovery -i ${RAW_INVENTORY} -vvv --tags mariadb --skip-tags common
}

function test_recovery {
    # Stop all nodes in the cluster, then recover.
    mariadb_stop
    mariadb_recovery
}

function test_backup {
    echo "Performing full backup"
    kolla-ansible mariadb-backup -i ${RAW_INVENTORY} -vvv --full
    # Sleep for 30 seconds, not because it's absolutely necessary.
    # The full backup is already completed at this point, as the
    # ansible job is waiting for the completion of the backup script
    # in the container on the controller side. It’s more of an
    # attempt at a "sort of" simulation of the usual elapsed time
    # since the last full backup for the incremental job, as some
    # data gets written within those 30 seconds.
    echo "Sleeping for 30 seconds"
    sleep 30
    kolla-ansible mariadb-backup -i ${RAW_INVENTORY} -vvv --incremental
}

function test_backup_with_retries {
    # Retry test_backup up to 3 times if it fails
    local max_retries=3
    local attempt=1

    while [[ $attempt -le $max_retries ]]; do
        echo "Attempt $attempt of $max_retries for test_backup"

        set +o errexit  # Temporarily disable errexit for retry logic
        test_backup
        result=$?
        set -o errexit  # Re-enable errexit after the attempt

        if [[ $result -eq 0 ]]; then
            echo "test_backup succeeded on attempt $attempt"
            return 0  # Exit the function if test_backup succeeds
        else
            echo "test_backup failed on attempt $attempt"
        fi

        if [[ $attempt -lt $max_retries ]]; then
            echo "Sleeping for 30 seconds before the next attempt"
            sleep 30  # Wait for 30 seconds before retrying
        fi

        attempt=$((attempt + 1))
    done

    echo "test_backup failed after $max_retries attempts"
    return 1  # Return an error if all attempts fail
}

function test_mariadb_logged {
    RAW_INVENTORY=/etc/kolla/inventory
    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate
    test_backup_with_retries
    test_recovery
}

function test_mariadb {
    echo "Testing MariaDB"
    test_mariadb_logged > /tmp/logs/ansible/test-mariadb 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing MariaDB failed. See ansible/test-mariadb for details"
    else
        echo "Successfully tested MariaDB. See ansible/test-mariadb for details"
    fi
    return $result
}

container_engine="${1:-docker}"
test_mariadb
