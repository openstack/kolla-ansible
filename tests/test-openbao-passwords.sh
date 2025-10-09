#!/bin/bash

set -o xtrace
set -o errexit

export PYTHONUNBUFFERED=1

function install_openbao {
    if [[ $BASE_DISTRO =~ (debian|ubuntu) ]]; then
        curl -fsSLO https://github.com/openbao/openbao/releases/download/v2.4.1/bao_2.4.1_linux_amd64.deb
        sudo dpkg -i bao_2.4.1_linux_amd64.deb
        rm -f bao_2.4.1_linux_amd64.deb
    else
        sudo dnf install -y https://github.com/openbao/openbao/releases/download/v2.4.1/bao_2.4.1_linux_amd64.rpm
    fi
}

function start_openbao {
    nohup bao server --dev &
    # Give Vault some time to warm up
    sleep 10
}

function test_openbao {
    TOKEN=$(bao token create -address 'http://127.0.0.1:8200' -field token)
    echo "${TOKEN}" | bao login -address 'http://127.0.0.1:8200' -
    bao kv put -address 'http://127.0.0.1:8200' secret/foo data=bar
}

function test_writepwd {
    TOKEN=$(bao token create -address 'http://127.0.0.1:8200' -field token)
    kolla-writepwd \
        --passwords /etc/kolla/passwords.yml \
        --vault-addr 'http://127.0.0.1:8200' \
        --vault-token ${TOKEN} \
        --vault-mount-point secret
}

function test_readpwd {
    TOKEN=$(bao token create -address 'http://127.0.0.1:8200' -field token)
    cp etc/kolla/passwords.yml /tmp/passwords-openbao.yml
    kolla-readpwd \
        --passwords /tmp/passwords-openbao.yml \
        --vault-addr 'http://127.0.0.1:8200' \
        --vault-token ${TOKEN} \
        --vault-mount-point secret
}

function teardown {
    pkill bao
}

function test_openbao_passwords {
    echo "Setting up development OpenBao server..."
    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate
    install_openbao
    start_openbao
    test_openbao
    echo "Write passwords to OpenBao..."
    test_writepwd
    echo "Read passwords from OpenBao..."
    test_readpwd
    echo "Cleaning up..."
    teardown
}

test_openbao_passwords
