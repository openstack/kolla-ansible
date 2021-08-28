#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function upgrade {
    local ansible_extra_vars
    RAW_INVENTORY=/etc/kolla/inventory
    # TODO(mgoddard): Remove this block in the Y cycle after chrony has been
    # dropped for a cycle.
    # NOTE(mgoddard): Remove the chrony container and install a host chrony
    # daemon.
    kolla-ansible -i ${RAW_INVENTORY} -vvv chrony-cleanup &> /tmp/logs/ansible/chrony-cleanup
    if [[ $(source /etc/os-release && echo $ID) = "centos" ]]; then
        chrony_service="chronyd"
        ansible_extra_vars=""
    else
        chrony_service="chrony"
        # Force the use of python3 on Debian and Ubuntu remote hosts. These distros
        # typically have an unversioned Python interpreter which links to python2.7.
        ansible_extra_vars="-e ansible_python_interpreter=/usr/bin/python3"
    fi
    ansible all -i $RAW_INVENTORY $ansible_extra_vars -m package -a 'name=chrony state=present' -b &> /tmp/logs/ansible/chrony-install
    ansible all -i $RAW_INVENTORY $ansible_extra_vars -m service -a 'name='$chrony_service' state=started enabled=yes' -b &>> /tmp/logs/ansible/chrony-install

    kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks &> /tmp/logs/ansible/upgrade-prechecks
    kolla-ansible -i ${RAW_INVENTORY} -vvv pull &> /tmp/logs/ansible/pull-upgrade
    kolla-ansible -i ${RAW_INVENTORY} -vvv upgrade &> /tmp/logs/ansible/upgrade
    kolla-ansible -i ${RAW_INVENTORY} -vvv check &> /tmp/logs/ansible/check-upgrade
}


upgrade
