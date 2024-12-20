#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function deploy_tenks_logged {
    . /etc/kolla/admin-openrc.sh

    echo "Creating IPA images for Ironic"
    ~/openstackclient-venv/bin/openstack image create --disk-format aki --container-format aki --private \
        --file /etc/kolla/config/ironic/ironic-agent.kernel ipa.vmlinuz
    ~/openstackclient-venv/bin/openstack image create --disk-format ari --container-format ari --private \
        --file /etc/kolla/config/ironic/ironic-agent.initramfs ipa.initramfs

    # Install a trivial script for ovs-vsctl that talks to containerised Open
    # vSwitch.
    sudo tee /usr/bin/ovs-vsctl >/dev/null <<EOF
#!/usr/bin/env bash

# Script installed onto the host to fool tenks into using the containerised
# Open vSwitch rather than installing its own.

sudo ${CONTAINER_ENGINE} exec openvswitch_vswitchd ovs-vsctl "\$@"
EOF
    sudo chmod 755 /usr/bin/ovs-vsctl

    # Install the Tenks venv.
    python3 -m venv ${TENKS_VENV_PATH}
    ${TENKS_VENV_PATH}/bin/pip install -U pip
    ${TENKS_VENV_PATH}/bin/pip install ${TENKS_SRC_PATH}

    local attempt
    attempt=1
    while ! ${TENKS_VENV_PATH}/bin/ansible-galaxy install \
            --role-file="${TENKS_SRC_PATH}/requirements.yml" \
            --roles-path="${TENKS_SRC_PATH}/ansible/roles/"; do
        echo "ansible-galaxy install failed, attempt $attempt"
        attempt=$((attempt+1))
        if [[ $attempt -eq 10 ]]; then
            echo "enough retrying, farewell"
            return 1
        fi
        sleep 10
    done

    # Run Tenks.
    ${TENKS_VENV_PATH}/bin/ansible-playbook \
        -vvv \
        --inventory "${TENKS_SRC_PATH}/ansible/inventory" \
        --extra-vars=@"$HOME/tenks.yml" \
        "${TENKS_SRC_PATH}/ansible/deploy.yml"
}

function deploy_tenks {
    echo "Configuring virtual bare metal via Tenks"
    deploy_tenks_logged $1 > /tmp/logs/ansible/deploy-tenks 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Deploying tenks failed. See ansible/deploy-tenks for details"
    else
        echo "Successfully deployed tenks. See ansible/deploy-tenks for details"
    fi
    return $result
}

deploy_tenks $1
