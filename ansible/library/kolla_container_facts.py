#!/usr/bin/env python

# Copyright 2016 99cloud
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

DOCUMENTATION = '''
---
module: kolla_container_facts
short_description: Module for collecting Docker container facts
description:
  - A module targeting at collecting Docker container facts. It is used for
    detecting whether the container is running on host in Kolla.
options:
  api_version:
    description:
      - The version of the api for docker-py to use when contacting docker
    required: False
    type: str
    default: auto
  name:
    description:
      - Name or names of the containers
    required: False
    type: str or list
author: Jeffrey Zhang
'''

EXAMPLES = '''
- hosts: all
  tasks:
    - name: Gather docker facts
      kolla_container_facts:

    - name: Gather glance container facts
      kolla_container_facts:
        name:
          - glance_api
          - glance_registry
'''

import docker


def main():
    argument_spec = dict(
        name=dict(required=False, type='list', default=[]),
        api_version=dict(required=False, type='str', default='auto')
    )

    module = AnsibleModule(argument_spec=argument_spec)

    results = dict(changed=False, _containers=[])
    client = docker.Client(version=module.params.get('api_version'))
    containers = client.containers()
    names = module.params.get('name')
    if names and not isinstance(names, list):
        names = [names]
    for container in containers:
        for container_name in container['Names']:
            # remove '/' prefix character
            container_name = container_name[1:]
            if names and container_name not in names:
                continue
            results['_containers'].append(container)
            results[container_name] = container
    module.exit_json(**results)


from ansible.module_utils.basic import *  # noqa
if __name__ == "__main__":
    main()
