#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

export PYTHONUNBUFFERED=1


function init_runonce {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate

    echo "Initialising OpenStack resources via init-runonce"
    KOLLA_DEBUG=1 tools/init-runonce |& gawk '{ print strftime("%F %T"), $0; }' &> /tmp/logs/ansible/init-runonce
}


init_runonce
