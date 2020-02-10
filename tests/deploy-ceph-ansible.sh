#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function setup_ceph_ansible {
    # Prepare virtualenv for ceph-ansible deployment
    # NOTE(mnasiadka): Use python2 on centos7 due to missing python3 selinux bindings
    if [[ $BASE_DISTRO == "centos" ]] && [[ $BASE_DISTRO_MAJOR_VERSION -eq 8 ]]; then
        virtualenv --system-site-packages ~/ceph-venv
    else
        virtualenv -p `which python2` --system-site-packages ~/ceph-venv
    fi
    ~/ceph-venv/bin/pip install -Ir requirements.txt
    ~/ceph-venv/bin/pip install -IU selinux
}

function deploy_ceph_ansible {
    RAW_INVENTORY=/etc/kolla/ceph-inventory

    . ~/ceph-venv/bin/activate

    cp site-container.yml.sample site-container.yml
    ansible-playbook -i ${RAW_INVENTORY} -e @/etc/kolla/ceph-ansible.yml -vvv site-container.yml --skip-tags=with_pkg &> /tmp/logs/ansible/deploy-ceph
}

setup_ceph_ansible
deploy_ceph_ansible
