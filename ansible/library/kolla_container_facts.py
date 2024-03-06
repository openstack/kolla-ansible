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

from abc import ABC
from abc import abstractmethod
from ansible.module_utils.basic import AnsibleModule
from traceback import format_exc


DOCUMENTATION = '''
---
module: kolla_container_facts
short_description: Module for collecting Docker container facts
description:
  - A module targeting at collecting Docker container facts. It is used for
    detecting whether the container is running on host in Kolla.
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
      - Name or names of the containers
    required: False
    type: str or list
  action:
    description:
      - The action to perform
    required: True
    type: str
author: Jeffrey Zhang
'''

EXAMPLES = '''
- hosts: all
  tasks:
    - name: Gather docker facts
      kolla_container_facts:
        container_engine: docker
      action: get_containers

    - name: Gather glance container facts
      kolla_container_facts:
        container_engine: docker
        name:
          - glance_api
          - glance_registry
        container_engine: podman
        action: get_containers
'''


class ContainerFactsWorker(ABC):
    def __init__(self, module):
        self.module = module
        self.results = dict(changed=False, _containers=[])
        self.params = module.params

    @abstractmethod
    def get_containers(self):
        pass


class DockerFactsWorker(ContainerFactsWorker):
    def __init__(self, module):
        super().__init__(module)
        try:
            import docker
        except ImportError:
            self.module.fail_json(
                msg="The docker library could not be imported")
        self.client = docker.APIClient(version=module.params.get(
                                       'api_version'))

    def get_containers(self):
        containers = self.client.containers()
        names = self.params.get('name')
        if names and not isinstance(names, list):
            names = [names]
        for container in containers:
            for container_name in container['Names']:
                # remove '/' prefix character
                container_name = container_name[1:]
                if names and container_name not in names:
                    continue
                self.results['_containers'].append(container)
                self.results[container_name] = container


class PodmanFactsWorker(ContainerFactsWorker):
    def __init__(self, module):
        try:
            import podman.errors as podmanError
            from podman import PodmanClient
        except ImportError:
            self.module.fail_json(
                msg="The podman library could not be imported")
        self.podmanError = podmanError
        super().__init__(module)
        self.client = PodmanClient(
            base_url="http+unix:/run/podman/podman.sock")

    def get_containers(self):
        try:
            containers = self.client.containers.list(
                all=True, ignore_removed=True)
        except self.podmanError.APIError as e:
            self.module.fail_json(failed=True,
                                  msg=f"Internal error: {e.explanation}")
        names = self.params.get('name')
        if names and not isinstance(names, list):
            names = [names]

        for container in containers:
            container.reload()
            container_name = container.attrs['Name']
            if container_name not in names:
                continue
            self.results['_containers'].append(container.attrs)
            self.results[container_name] = container.attrs


def main():
    argument_spec = dict(
        name=dict(required=False, type='list', default=[]),
        api_version=dict(required=False, type='str', default='auto'),
        container_engine=dict(required=True, type='str'),
        action=dict(required=True, type='str',
                    choices=['get_containers']),
    )

    module = AnsibleModule(argument_spec=argument_spec)

    cw: ContainerFactsWorker = None
    try:
        if module.params.get('container_engine') == 'docker':
            cw = DockerFactsWorker(module)
        else:
            cw = PodmanFactsWorker(module)

        result = bool(getattr(cw, module.params.get('action'))())
        module.exit_json(result=result, **cw.results)
    except Exception:
        module.fail_json(changed=True, msg=repr(format_exc()),
                         **getattr(cw, 'result', {}))


if __name__ == "__main__":
    main()
