#!/usr/bin/env bash

# NOTE(hinermar): During deployment, Ansible handles module discovery
# automatically. In testing environment this feature is
# not present so it's necessary to link module files to environment
# package directory so they can be discovered by python interpreter.


local_module_utils=${1}/ansible/module_utils
env_module_utils=$(/usr/bin/env python -c "import ansible; print(ansible.__path__[0] + '/module_utils')")

for file_path in ${local_module_utils}/*.py; do
    file_name=$(basename ${file_path})
    source=$(realpath ${file_path})
    destination=$(realpath ${env_module_utils})/${file_name}
    ln -fs ${source} ${destination}
done
