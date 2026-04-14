#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1

function init_pebble {

    sudo echo "[i] Pulling letsencrypt/pebble" > /tmp/logs/ansible/certificates
    sudo docker pull quay.io/openstack.kolla/pebble:latest &>> /tmp/logs/ansible/certificates

    sudo echo "[i] Force removing old pebble container" &>> /tmp/logs/ansible/certificates
    sudo docker rm -f pebble &>> /tmp/logs/ansible/certificates

    sudo echo "[i] Run new pebble container" &>> /tmp/logs/ansible/certificates
    sudo docker run --name pebble --rm -d -e "PEBBLE_VA_NOSLEEP=1" -e "PEBBLE_VA_ALWAYS_VALID=1" --net=host quay.io/openstack.kolla/pebble:latest &>> /tmp/logs/ansible/certificates

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
        kolla-ansible certificates -i ${RAW_INVENTORY} -vvv > /tmp/logs/ansible/certificates
    fi
    if [[ "$LE_ENABLED" = "True" ]]; then
        init_pebble
        pebble_cacert
    fi

    #TODO(inc0): Post-deploy complains that /etc/kolla is not writable. Probably we need to include become there
    sudo chmod -R 777 /etc/kolla
}

function migrate_valkey {

    RAW_INVENTORY=/etc/kolla/inventory
    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate

    if grep -q '^enable_redis:' /etc/kolla/globals.yml; then
        sed -i 's/^enable_redis:.*/enable_redis: "no"/' /etc/kolla/globals.yml
    else
        echo 'enable_redis: "no"' >> /etc/kolla/globals.yml
    fi

    if grep -q '^enable_valkey:' /etc/kolla/globals.yml; then
        sed -i 's/^enable_valkey:.*/enable_valkey: "yes"/' /etc/kolla/globals.yml
    else
        echo 'enable_valkey: "yes"' >> /etc/kolla/globals.yml
    fi

    # Keep the initial Valkey password aligned with the current Redis password.
    REDIS_PASSWORD=$(awk -F': ' '/^redis_master_password:/ {print $2}' /etc/kolla/passwords.yml)
    if grep -q '^valkey_master_password:' /etc/kolla/passwords.yml; then
        sed -i "s|^valkey_master_password:.*|valkey_master_password: ${REDIS_PASSWORD}|" /etc/kolla/passwords.yml
    else
        echo "valkey_master_password: ${REDIS_PASSWORD}" >> /etc/kolla/passwords.yml
    fi

    kolla-ansible pull -i ${RAW_INVENTORY} -t valkey -vvv &> /tmp/logs/ansible/pull-valkey
    kolla-ansible migrate-valkey -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/migrate-valkey
}

function deploy {

    RAW_INVENTORY=/etc/kolla/inventory
    source $KOLLA_ANSIBLE_VENV_PATH/bin/activate

    #TODO(inc0): Post-deploy complains that /etc/kolla is not writable. Probably we need to include become there
    sudo chmod -R 777 /etc/kolla

    certificates

    # Actually do the deployment
    kolla-ansible prechecks -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/deploy-prechecks
    kolla-ansible pull -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/pull
    kolla-ansible deploy -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/deploy
    kolla-ansible post-deploy -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/post-deploy

    if [[ $MIGRATE_VALKEY == 'yes' ]]; then
        migrate_valkey
    fi

    if [[ $HAS_UPGRADE == 'no' ]]; then
        kolla-ansible validate-config -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/validate-config
        #TODO(r-krcek) check can be moved out of the if statement in the flamingo cycle
        kolla-ansible check -i ${RAW_INVENTORY} -vvv &> /tmp/logs/ansible/check
    fi
}


deploy
