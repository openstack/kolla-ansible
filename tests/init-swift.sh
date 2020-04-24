#!/bin/bash

set -o xtrace
set -o errexit


function init_swift_logged {
    next_port=6000

    # the order is important due to port incrementation
    for ring in object account container; do
        # create the *.builder files
        sudo docker run \
            --rm \
            -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
            $KOLLA_SWIFT_BASE_IMAGE \
            swift-ring-builder \
            /etc/kolla/config/swift/$ring.builder create 10 3 1

        # add nodes to them
        for node in ${STORAGE_NODES[@]}; do
            sudo docker run \
                --rm \
                -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
                $KOLLA_SWIFT_BASE_IMAGE \
                swift-ring-builder \
                /etc/kolla/config/swift/$ring.builder add r1z1-${node}:$next_port/d0 1
        done

        # create the *.ring.gz files
        sudo docker run \
            --rm \
            -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
            $KOLLA_SWIFT_BASE_IMAGE \
            swift-ring-builder \
            /etc/kolla/config/swift/$ring.builder rebalance

        # display contents for debugging
        sudo docker run \
            --rm \
            -v /etc/kolla/config/swift/:/etc/kolla/config/swift/ \
            $KOLLA_SWIFT_BASE_IMAGE \
            swift-ring-builder \
            /etc/kolla/config/swift/$ring.builder

        # next ring = next port
        next_port=$((next_port+1))
    done
}

function init_swift {
    echo "Initialising Swift"
    init_swift_logged &> /tmp/logs/ansible/init-swift
}


init_swift
