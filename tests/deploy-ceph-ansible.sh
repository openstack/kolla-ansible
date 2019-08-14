#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function setup_ceph_ansible {
    # FIXME(mnasiadka): Use python3 when we move to CentOS 8
    # (there are no python3 selinux bindings for 3 on C7)
    # see https://bugs.centos.org/view.php?id=16389

    # Prepare virtualenv for ceph-ansible deployment
    virtualenv --system-site-packages ~/ceph-venv
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
