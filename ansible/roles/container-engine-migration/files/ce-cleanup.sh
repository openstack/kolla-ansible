#!/usr/bin/env bash

set -o xtrace
set -o errexit
set -o pipefail

# default to docker if not specified
engine="${1:-docker}"
shift 1

if ! [[ "$engine" =~ ^(docker|podman)$ ]]; then
    echo "Invalid container engine: ${engine}"
    exit 1
fi

echo "Using container engine: $engine"

echo "Looking for containers, images and volumes to remove..."
containers_to_kill=$(sudo $engine ps --filter "label=kolla_version" --format "{{.Names}}" -a)
images_to_remove=$(sudo $engine images --filter "label=kolla_version" -q -a)

if [ -n "${containers_to_kill}" ]; then
    volumes_to_remove=$(sudo $engine inspect -f '{{range .Mounts}} {{printf "%s\n" .Name }}{{end}}' ${containers_to_kill} | \
        grep -Ev '(^\s*$)' | sort | uniq)

    echo "Stopping containers..."
    for container in ${containers_to_kill}; do
        sudo systemctl disable kolla-${container}-container.service
        sudo systemctl stop kolla-${container}-container.service
        sudo systemctl is-failed kolla-${container}-container.service && \
        sudo systemctl reset-failed kolla-${container}-container.service
    done

    echo "Removing containers..."
    (sudo $engine rm -f ${containers_to_kill} 2>&1) > /dev/null
fi

echo "Removing any remaining unit files..."
sudo rm -f /etc/systemd/system/kolla-*-container.service
sudo systemctl daemon-reload

echo "Removing images..."
if [ -n "${images_to_remove}" ]; then
    (sudo $engine rmi -f ${images_to_remove} 2>&1) > /dev/null
fi

echo "Removing volumes..."
if [ -n "${volumes_to_remove}" ]; then
    (sudo $engine volume rm -f ${volumes_to_remove} 2>&1) > /dev/null
fi

echo "Performing final cleanup of any remaining unused resources..."
sudo $engine system prune -a -f

echo "All cleaned up!"
