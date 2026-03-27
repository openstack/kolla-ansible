#!/bin/bash

running_nodes=$(docker exec rabbitmq rabbitmqctl cluster_status \
    | awk '/Running Nodes/{f=1;next}/Versions/{f=0}f{print $1}')

streams=$(docker exec rabbitmq rabbitmqctl list_queues name type --silent | awk '/stream/ {print $1}')

for stream in $streams; do
    stream_nodes=$(docker exec rabbitmq rabbitmq-streams stream_status -s $stream \
        | awk 'NR>3 {print $4}')

    missing=0
    for node in $running_nodes; do
        if ! grep -qx "$node" <<< "$stream_nodes"; then
            echo "MISSING replica of $stream on $node"
            missing=1
            docker exec rabbitmq rabbitmq-streams add_replica $stream $node
        fi
    done

    if [ $missing -eq 0 ]; then
        echo "OK: All running nodes have a replica of $stream"
    fi
done
