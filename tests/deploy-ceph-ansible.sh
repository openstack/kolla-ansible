#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function setup_ceph_ansible {
    # Prepare virtualenv for ceph-ansible deployment
    python3 -m venv --system-site-packages ~/ceph-venv
    # NOTE(mgoddard): We need a recent pip to install the latest cryptography
    # library. See https://github.com/pyca/cryptography/issues/5753
    ~/ceph-venv/bin/pip install -I 'pip>=19.1.1'
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
