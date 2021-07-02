#!/bin/bash

set -o xtrace
set -o errexit

export PYTHONUNBUFFERED=1

function install_vault {
    if [[ "debian" == $BASE_DISTRO ]]; then
        curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
        sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
        sudo apt-get update -y && sudo apt-get install -y vault jq
    else
        sudo dnf install -y yum-utils
        sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
        sudo dnf install -y vault jq
    fi
}

function start_vault {
    nohup vault server --dev &
    # Give Vault some time to warm up
    sleep 10
}

function test_vault {
    TOKEN=$(vault token create -address 'http://127.0.0.1:8200' -format json | jq '.auth.client_token' --raw-output)
    echo "${TOKEN}" | vault login -address 'http://127.0.0.1:8200' -
    vault kv put -address 'http://127.0.0.1:8200' secret/foo data=bar
}

function test_writepwd {
    TOKEN=$(vault token create -address 'http://127.0.0.1:8200' -format json | jq '.auth.client_token' --raw-output)
    kolla-writepwd \
        --passwords /etc/kolla/passwords.yml \
        --vault-addr 'http://127.0.0.1:8200' \
        --vault-token ${TOKEN} \
        --vault-mount-point secret
}

function test_readpwd {
    TOKEN=$(vault token create -address 'http://127.0.0.1:8200' -format json | jq '.auth.client_token' --raw-output)
    cp etc/kolla/passwords.yml /tmp/passwords-hashicorp-vault.yml
    kolla-readpwd \
        --passwords /tmp/passwords-hashicorp-vault.yml \
        --vault-addr 'http://127.0.0.1:8200' \
        --vault-token ${TOKEN} \
        --vault-mount-point secret
}

function teardown {
    pkill vault
}

function test_hashicorp_vault_passwords {
    echo "Setting up development Vault server..."
    install_vault
    start_vault
    test_vault
    echo "Write passwords to Hashicorp Vault..."
    test_writepwd
    echo "Read passwords from Hashicorp Vault..."
    test_readpwd
    echo "Cleaning up..."
    teardown
}

test_hashicorp_vault_passwords
