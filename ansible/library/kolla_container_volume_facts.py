# Copyright 2023 StackHPC
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


import docker

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: kolla_container_volume_facts
short_description: Module for collecting Docker container volume facts
description:
  - A module targeted at collecting Docker container volume facts. It is used
    for detecting whether the container volume exists on a host.
options:
  container_engine:
    description:
      - Name of container engine to use
    required: True
    type: str
  api_version:
    description:
      - The version of the api for docker-py to use when contacting docker
    required: False
    type: str
    default: auto
  name:
    description:
      - Name or names of the container volumes
    required: False
    type: str or list
author: Jeffrey Zhang / Michal Nasiadka
'''

EXAMPLES = '''
- hosts: all
  tasks:
    - name: Gather docker facts
      kolla_container_volume_facts:

    - name: Gather glance container facts
      kolla_container_volume_facts:
        container_engine: docker
        name:
          - glance_api
          - glance_registry
'''


def get_docker_client():
    return docker.APIClient


def main():
    argument_spec = dict(
        name=dict(required=False, type='list', default=[]),
        api_version=dict(required=False, type='str', default='auto'),
        container_engine=dict(required=True, type='str')
    )

    module = AnsibleModule(argument_spec=argument_spec)

    results = dict(changed=False, _volumes=[])
    client = get_docker_client()(version=module.params.get('api_version'))
    volumes = client.volumes()
    names = module.params.get('name')
    if names and not isinstance(names, list):
        names = [names]
    for volume in volumes['Volumes']:
        volume_name = volume['Name']
        if names and volume_name not in names:
            continue
        results['_volumes'].append(volume)
        results[volume_name] = volume
    module.exit_json(**results)


if __name__ == "__main__":
    main()
