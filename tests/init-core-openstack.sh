#!/bin/bash

set -o xtrace
set -o errexit

export PYTHONUNBUFFERED=1


function init_runonce {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate

    echo "Initialising OpenStack resources via init-runonce"
    tools/init-runonce &> /tmp/logs/ansible/init-runonce
}


init_runonce
