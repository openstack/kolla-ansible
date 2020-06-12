#!/bin/bash

set -o xtrace
set -o errexit

# Enable unbuffered output for Ansible in Jenkins.
export PYTHONUNBUFFERED=1


function test_tacker {
    echo "TESTING: Tacker VIM,VNFD and VNF creation"
    sh contrib/demos/tacker/deploy-tacker-demo
    openstack vim list
    openstack vnf list
    openstack vnf descriptor list

    while [[ $(openstack vnf show kolla-sample-vnf -f value -c status) != "ACTIVE" ]]; do
            echo "VNF not running yet"
            attempt=$((attempt+1))
            if [[ $attempt -eq 10 ]]; then
                echo "VNF failed to start"
                openstack vnf show kolla-sample-vnf
                return 1
            fi
            sleep 10
        done
}

function test_barbican {
    echo "TESTING: Barbican"
    openstack secret list
}

function test_mistral {
    echo "TESTING: Mistral"
    openstack workflow list
    openstack workflow execution list
    openstack action execution list
}

function test_nova {
    echo "TESTING: Nova"
    openstack server list
}

function test_heat {
    echo "TESTING: Heat"
    openstack stack list
}

function test_scenario_nfv_logged {
    . /etc/kolla/admin-openrc.sh
    . ~/openstackclient-venv/bin/activate

    test_tacker
    test_barbican
    test_mistral
    test_nova
    test_heat
}

function test_scenario_nfv {
    echo "Testing Scenario NFV"
    test_scenario_nfv_logged > /tmp/logs/ansible/test-scenario-nfv 2>&1
    result=$?
    if [[ $result != 0 ]]; then
        echo "Testing Scenario NFV failed. See ansible/test-scenario-nfv for details"
    else
        echo "Successfully Scenario NFV. See ansible/test-scenario-nfv for details"
    fi
    return $result
}

test_scenario_nfv
