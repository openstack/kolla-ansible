#!/usr/bin/env bash
#
# This script can be used to check user privilege to execute
# docker or podman commands depending on CONTAINER_ENGINE 
# environment variable

function check_dockerexecute {
    sudo $CONTAINER_ENGINE ps &>/dev/null
    return_val=$?
    if [ $return_val -ne 0 ]; then
        echo "User $USER can't seem to run ${CONTAINER_ENGINE^} commands. Verify product documentation to allow user to execute ${CONTAINER_ENGINE^} commands" 1>&2
        exit 1
    fi
}
check_dockerexecute
