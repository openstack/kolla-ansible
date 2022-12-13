# Copyright 2015 Sam Yaple
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

# FIXME(yoctozepto): this module does *not* validate "common_options" which are
# a hacky way to seed most usages of kolla_docker in kolla-ansible ansible
# playbooks - caution has to be exerted when setting "common_options"

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.kolla_docker_worker import DockerWorker

DOCUMENTATION = '''
---
module: kolla_docker
short_description: Module for controlling Docker
description:
     - A module targeting at controlling Docker as used by Kolla.
options:
  common_options:
    description:
      - A dict containing common params such as login info
    required: False
    type: dict
    default: dict()
  action:
    description:
      - The action the module should take
    required: True
    type: str
    choices:
      - compare_container
      - compare_image
      - create_volume
      - ensure_image
      - get_container_env
      - get_container_state
      - pull_image
      - remove_container
      - remove_image
      - remove_volume
      - recreate_or_restart_container
      - restart_container
      - start_container
      - stop_container
      - stop_container_and_remove_container
  api_version:
    description:
      - The version of the api for docker-py to use when contacting docker
    required: False
    type: str
    default: auto
  auth_email:
    description:
      - The email address used to authenticate
    required: False
    type: str
  auth_password:
    description:
      - The password used to authenticate
    required: False
    type: str
  auth_registry:
    description:
      - The registry to authenticate
    required: False
    type: str
  auth_username:
    description:
      - The username used to authenticate
    required: False
    type: str
  command:
    description:
      - The command to execute in the container
    required: False
    type: str
  detach:
    description:
      - Detach from the container after it is created
    required: False
    default: True
    type: bool
  name:
    description:
      - Name of the container or volume to manage
    required: False
    type: str
  environment:
    description:
      - The environment to set for the container
    required: False
    type: dict
  image:
    description:
      - Name of the docker image
    required: False
    type: str
  ipc_mode:
    description:
      - Set docker ipc namespace
    required: False
    type: str
    default: None
    choices:
      - host
  cap_add:
    description:
      - Add capabilities to docker container
    required: False
    type: list
    default: list()
  security_opt:
    description:
      - Set container security profile
    required: False
    type: list
    default: list()
  labels:
    description:
      - List of labels to apply to container
    required: False
    type: dict
    default: dict()
  pid_mode:
    description:
      - Set docker pid namespace
    required: False
    type: str
    default: None
    choices:
      - host
  cgroupns_mode:
    description:
      - Set docker cgroups namespace (default depends on Docker config)
      - Supported only with Docker 20.10 (Docker API 1.41) and later
    required: False
    type: str
    default: None
    choices:
      - private
      - host
  privileged:
    description:
      - Set the container to privileged
    required: False
    default: False
    type: bool
  remove_on_exit:
    description:
      - When not detaching from container, remove on successful exit
    required: False
    default: True
    type: bool
  restart_policy:
    description:
      - When docker restarts the container (does not affect checks)
    required: False
    type: str
    choices:
      - no
      - on-failure
      - always
      - unless-stopped
  restart_retries:
    description:
      - How many times to attempt a restart if 'on-failure' policy is set
    type: int
    default: 10
  tmpfs:
    description:
      - List of paths to mount as tmpfs.
    required: False
    type: list
  volumes:
    description:
      - Set volumes for docker to use
    required: False
    type: list
  volumes_from:
    description:
      - Name or id of container(s) to use volumes from
    required: True
    type: list
  state:
    description:
      - Check container status
    required: False
    type: str
    choices:
      - running
      - exited
      - paused
  tty:
    description:
      - Allocate TTY to container
    required: False
    default: False
    type: bool
  client_timeout:
    description:
      - Docker client timeout in seconds
    required: False
    default: 120
    type: int
  healthcheck:
    description:
      - Container healthcheck configuration
    required: False
    default: dict()
    type: dict
author: Sam Yaple
'''

EXAMPLES = '''
- hosts: kolla_docker
  tasks:
    - name: Start container
      kolla_docker:
        image: ubuntu
        name: test_container
        action: start_container
    - name: Remove container
      kolla_docker:
        name: test_container
        action: remove_container
    - name: Pull image without starting container
      kolla_docker:
        action: pull_image
        image: private-registry.example.com:5000/ubuntu
    - name: Create named volume
      kolla_docker:
        action: create_volume
        name: name_of_volume
    - name: Remove named volume
      kolla_docker:
        action: remove_volume
        name: name_of_volume
    - name: Remove image
      kolla_docker:
        action: remove_image
        image: name_of_image
'''


def generate_module():
    # NOTE(jeffrey4l): add empty string '' to choices let us use
    # pid_mode: "{{ service.pid_mode | default ('') }}" in yaml
    argument_spec = dict(
        common_options=dict(required=False, type='dict', default=dict()),
        action=dict(required=True, type='str',
                    choices=['compare_container',
                             'compare_image',
                             'create_volume',
                             'ensure_image',
                             'get_container_env',
                             'get_container_state',
                             'pull_image',
                             'recreate_or_restart_container',
                             'remove_container',
                             'remove_image',
                             'remove_volume',
                             'restart_container',
                             'start_container',
                             'stop_container',
                             'stop_and_remove_container']),
        api_version=dict(required=False, type='str', default='auto'),
        auth_email=dict(required=False, type='str'),
        auth_password=dict(required=False, type='str', no_log=True),
        auth_registry=dict(required=False, type='str'),
        auth_username=dict(required=False, type='str'),
        command=dict(required=False, type='str'),
        detach=dict(required=False, type='bool', default=True),
        labels=dict(required=False, type='dict', default=dict()),
        name=dict(required=False, type='str'),
        environment=dict(required=False, type='dict'),
        healthcheck=dict(required=False, type='dict'),
        image=dict(required=False, type='str'),
        ipc_mode=dict(required=False, type='str', choices=['',
                                                           'host',
                                                           'private',
                                                           'shareable']),
        cap_add=dict(required=False, type='list', default=list()),
        security_opt=dict(required=False, type='list', default=list()),
        pid_mode=dict(required=False, type='str', choices=['host', '']),
        cgroupns_mode=dict(required=False, type='str',
                           choices=['private', 'host']),
        privileged=dict(required=False, type='bool', default=False),
        graceful_timeout=dict(required=False, type='int', default=10),
        remove_on_exit=dict(required=False, type='bool', default=True),
        restart_policy=dict(required=False, type='str', choices=[
                            'no',
                            'on-failure',
                            'always',
                            'unless-stopped']),
        restart_retries=dict(required=False, type='int', default=10),
        state=dict(required=False, type='str', default='running',
                   choices=['running',
                            'exited',
                            'paused']),
        tls_verify=dict(required=False, type='bool', default=False),
        tls_cert=dict(required=False, type='str'),
        tls_key=dict(required=False, type='str'),
        tls_cacert=dict(required=False, type='str'),
        tmpfs=dict(required=False, type='list'),
        volumes=dict(required=False, type='list'),
        volumes_from=dict(required=False, type='list'),
        dimensions=dict(required=False, type='dict', default=dict()),
        tty=dict(required=False, type='bool', default=False),
        client_timeout=dict(required=False, type='int', default=120),
        ignore_missing=dict(required=False, type='bool', default=False),
    )
    required_if = [
        ['action', 'pull_image', ['image']],
        ['action', 'start_container', ['image', 'name']],
        ['action', 'compare_container', ['name']],
        ['action', 'compare_image', ['name']],
        ['action', 'create_volume', ['name']],
        ['action', 'ensure_image', ['image']],
        ['action', 'get_container_env', ['name']],
        ['action', 'get_container_state', ['name']],
        ['action', 'recreate_or_restart_container', ['name']],
        ['action', 'remove_container', ['name']],
        ['action', 'remove_image', ['image']],
        ['action', 'remove_volume', ['name']],
        ['action', 'restart_container', ['name']],
        ['action', 'stop_container', ['name']],
        ['action', 'stop_and_remove_container', ['name']],
    ]
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=required_if,
        bypass_checks=False
    )

    new_args = module.params.pop('common_options', dict())

    # NOTE(jeffrey4l): merge the environment
    env = module.params.pop('environment', dict())
    if env:
        new_args['environment'].update(env)

    for key, value in module.params.items():
        if key in new_args and value is None:
            continue
        new_args[key] = value

    # if pid_mode = ""/None/False, remove it
    if not new_args.get('pid_mode', False):
        new_args.pop('pid_mode', None)
    # if ipc_mode = ""/None/False, remove it
    if not new_args.get('ipc_mode', False):
        new_args.pop('ipc_mode', None)

    module.params = new_args
    return module


def main():
    module = generate_module()

    dw = None
    try:
        dw = DockerWorker(module)
        # TODO(inc0): We keep it bool to have ansible deal with consistent
        # types. If we ever add method that will have to return some
        # meaningful data, we need to refactor all methods to return dicts.
        result = bool(getattr(dw, module.params.get('action'))())
        module.exit_json(changed=dw.changed, result=result, **dw.result)
    except Exception:
        module.fail_json(changed=True, msg=repr(traceback.format_exc()),
                         **getattr(dw, 'result', {}))


if __name__ == '__main__':
    main()
