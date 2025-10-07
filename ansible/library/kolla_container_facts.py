# Copyright 2016 99cloud
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

from ansible.module_utils.basic import AnsibleModule
from traceback import format_exc


DOCUMENTATION = '''
---
module: kolla_container_facts
short_description: Module for collecting container facts
description:
  - A module targeted at collecting container facts. It is used for
    retrieving data about containers like their environment or state.
options:
  container_engine:
    description:
      - Name of container engine to use
    required: True
    type: str
  api_version:
    description:
      - The version of the API for container SDK to use
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
      - The action "get_containers" only returns running containers, unless
        argument get_all_containers is True
    required: True
    type: str
    choices:
      - get_containers
      - get_container_env
      - get_container_state
  args:
    description:
      - Additional arguments for actions
    required: False
    type: dict
    elements: dict
    suboptions:
      get_all_containers:
        description:
          - Get all containers, even stopped containers when
            performing action "get_containers"
        type: bool
        required: False
        default: False
author: Jeffrey Zhang, Michal Nasiadka, Roman Krček, Ivan Halomi
'''

EXAMPLES = '''
- hosts: all
  tasks:
    - name: Gather docker facts for running containers
      kolla_container_facts:
        container_engine: docker
        action: get_containers

    - name: Gather docker facts for all containers
      kolla_container_facts:
        container_engine: docker
        action: get_containers
        args:
          get_all_containers: true

    - name: Gather glance container facts
      kolla_container_facts:
        container_engine: docker
        name:
          - glance_api
        container_engine: podman
        action: get_containers

    - name: Get Horizon container state
      kolla_container_facts:
        container_engine: podman
        name: horizon
        action: get_containers_state

    - name: Get Glance container environment
      kolla_container_facts:
        container_engine: docker
        name:
          - glance_api
        action: get_containers_env

    - name: Gather glance volume facts
      kolla_container_facts:
        container_engine: docker
        name:
          - glance_api
        action: get_volumes

    - name: Gather all volume facts
      kolla_container_facts:
        container_engine: docker
        action: get_volumes

    - name: Get container names
      kolla_container_facts:
        container_engine: docker
        action: get_containers_names
'''


class ContainerFactsWorker():
    def __init__(self, module):
        self.module = module
        self.params = module.params
        self.result = dict(changed=False)

    def _get_container_info(self, name: str) -> dict:
        """Return info about container if it exists."""
        try:
            cont = self.client.containers.get(name)
            return cont.attrs
        except self.containerError.NotFound:
            self.module.fail_json(msg="No such container: {}".format(name))
            return None

    def _remap_envs(self, envs_raw: list) -> dict:
        """Split list of environment variables separated by '=' to dict.

        Example item in list could be KOLLA_BASE_DISTRO=ubuntu, which
        would breakdown to {'KOLLA_BASE_DISTRO':'ubuntu'}
        """
        envs = dict()
        for env in envs_raw:
            if '=' in env:
                key, value = env.split('=', 1)
            else:
                key, value = env, ''
            envs[key] = value
        return envs

    def get_containers_names(self):
        """Handles when module is called with action get_containers_names"""
        containers = self.client.containers.list()
        names = [cont.name for cont in containers]
        self.result['container_names'] = names

    def get_containers(self):
        """Handle when module is called with action get_containers"""
        names = self.params.get('name')
        args = self.params.get('args', {})
        get_all_containers = args.get('get_all_containers', False)
        self.result['containers'] = dict()

        containers = self.client.containers.list(all=get_all_containers)
        for container in containers:
            container.reload()
            container_name = container.name
            if names and container_name not in names:
                continue
            # NOTE(r-krcek): For performance reasons don't include
            # healthcheck logs. It can contain MBs worth of data!
            container.attrs["State"].get("Health", dict()).pop("Log", None)
            self.result['containers'][container_name] = container.attrs

    def get_containers_state(self):
        """Handle when module is called with action get_containers_state"""
        # NOTE(r-krcek): This function can be removed when bifrost
        # role switches to modern format
        names = self.params.get('name')
        self.result['states'] = dict()

        for name in names:
            cont = self._get_container_info(name)
            if cont:
                self.result['states'][name] = cont["State"]["Status"]

    def get_containers_env(self):
        """Handle when module is called with action get_containers_state"""
        # NOTE(r-krcek): This function can be removed when bifrost
        # role switches to modern format
        names = self.params.get('name')
        self.result['envs'] = dict()

        for name in names:
            cont = self._get_container_info(name)
            if cont:
                envs = self._remap_envs(cont['Config']['Env'])
                self.result['envs'][name] = envs

    def get_volumes(self):
        """Handles when module is called with action get_volumes."""
        names = self.params.get('name')
        self.result['volumes'] = dict()

        if isinstance(names, str):
            names = [names]

        volumes = self.client.volumes.list()
        for volume in volumes:
            if names and volume.name not in names:
                continue
            self.result['volumes'][volume.name] = volume.attrs


class DockerFactsWorker(ContainerFactsWorker):
    def __init__(self, module):
        try:
            import docker
            import docker.errors as dockerError
        except ImportError:
            self.module.fail_json(
                msg="The docker library could not be imported")
        super().__init__(module)
        self.client = docker.DockerClient(
            base_url='http+unix:/var/run/docker.sock',
            version=module.params.get('api_version'))
        self.containerError = dockerError


class PodmanFactsWorker(ContainerFactsWorker):
    def __init__(self, module):
        try:
            import podman.errors as podmanError
            from podman import PodmanClient
        except ImportError:
            self.module.fail_json(
                msg="The podman library could not be imported")
        super().__init__(module)
        self.client = PodmanClient(
            base_url="http+unix:/run/podman/podman.sock")
        self.containerError = podmanError


def main():
    argument_spec = dict(
        name=dict(required=False, type='list', default=[]),
        api_version=dict(required=False, type='str', default='auto'),
        container_engine=dict(required=True, type='str'),
        action=dict(required=True, type='str',
                    choices=['get_containers',
                             'get_containers_env',
                             'get_volumes',
                             'get_containers_names',
                             'get_containers_state']),
        args=dict(
            type='dict',
            required=False,
            default={},
            options=dict(
                get_all_containers=dict(required=False,
                                        type='bool',
                                        default=False)
            )
        )
    )

    required_if = [
        ['action', 'get_containers_env', ['name']],
        ['action', 'get_containers_state', ['name']],
    ]
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=required_if,
        bypass_checks=False
    )

    cfw: ContainerFactsWorker = None
    try:
        if module.params.get('container_engine') == 'docker':
            cfw = DockerFactsWorker(module)
        else:
            cfw = PodmanFactsWorker(module)

        result = bool(getattr(cfw, module.params.get('action'))())
        module.exit_json(result=result, **cfw.result)
    except Exception:
        module.fail_json(changed=True, msg=repr(format_exc()),
                         **getattr(cfw, 'result', {}))


if __name__ == "__main__":
    main()
