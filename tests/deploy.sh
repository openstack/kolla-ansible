#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function init_pebble {

    sudo echo "[i] Pulling letsencrypt/pebble" > /tmp/logs/ansible/certificates
    sudo docker pull letsencrypt/pebble &>> /tmp/logs/ansible/certificates

    sudo echo "[i] Force removing old pebble container" &>> /tmp/logs/ansible/certificates
    sudo docker rm -f pebble &>> /tmp/logs/ansible/certificates

    sudo echo "[i] Run new pebble container" &>> /tmp/logs/ansible/certificates
    sudo docker run --name pebble --rm -d -e "PEBBLE_VA_NOSLEEP=1" -e "PEBBLE_VA_ALWAYS_VALID=1" --net=host letsencrypt/pebble &>> /tmp/logs/ansible/certificates

    sudo echo "[i] Wait for pebble container be up" &>> /tmp/logs/ansible/certificates
    # wait until pebble starts
    while ! sudo docker logs pebble | grep -q "Listening on"; do
        sleep 1
    done
    sudo echo "[i] Wait for pebble container done" &>> /tmp/logs/ansible/certificates

    sudo echo "[i] Pebble container logs" &>> /tmp/logs/ansible/certificates
    sudo docker logs pebble &>> /tmp/logs/ansible/certificates
}

function pebble_cacert {

    sudo docker cp pebble:/test/certs/pebble.minica.pem /etc/kolla/certificates/ca/pebble-root.crt
    sudo curl -k -s -o /etc/kolla/certificates/ca/pebble.crt -v https://127.0.0.1:15000/roots/0
}

function certificates {

    RAW_INVENTORY=/etc/kolla/inventory
    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate

    # generate self-signed certificates for the optional internal TLS tests
    if [[ "$TLS_ENABLED" = "True" ]]; then
        kolla-ansible -i ${RAW_INVENTORY} -vvv certificates > /tmp/logs/ansible/certificates
    fi
    if [[ "$LE_ENABLED" = "True" ]]; then
        init_pebble
        pebble_cacert
    fi

    #TODO(inc0): Post-deploy complains that /etc/kolla is not writable. Probably we need to include become there
    sudo chmod -R 777 /etc/kolla
}


function deploy {

    RAW_INVENTORY=/etc/kolla/inventory
    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate

    #TODO(inc0): Post-deploy complains that /etc/kolla is not writable. Probably we need to include become there
    sudo chmod -R 777 /etc/kolla

    certificates

    # Actually do the deployment
    kolla-ansible -i ${RAW_INVENTORY} -vvv prechecks &> /tmp/logs/ansible/deploy-prechecks
    kolla-ansible -i ${RAW_INVENTORY} -vvv pull &> /tmp/logs/ansible/pull
    kolla-ansible -i ${RAW_INVENTORY} -vvv deploy &> /tmp/logs/ansible/deploy
    kolla-ansible -i ${RAW_INVENTORY} -vvv post-deploy &> /tmp/logs/ansible/post-deploy

    if [[ $HAS_UPGRADE == 'no' ]]; then
        kolla-ansible -i ${RAW_INVENTORY} -vvv validate-config &> /tmp/logs/ansible/validate-config
    fi
}


deploy
