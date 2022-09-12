# Copyright 2016 99cloud Inc.
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

import json
import re

from ansible.module_utils.basic import AnsibleModule

from ast import literal_eval
from shlex import split

DOCUMENTATION = '''
---
module: kolla_toolbox
short_description: >
  Module for invoking ansible module in kolla_toolbox container.
description:
  - A module targerting at invoking ansible module in kolla_toolbox
    container as used by Kolla project.
options:
  container_engine:
    description:
      - Name of container engine to use
    required: True
    type: str
  module_name:
    description:
      - The module name to invoke
    required: True
    type: str
  module_args:
    description:
      - The module args use by the module
    required: False
    type: str or dict
  module_extra_vars:
    description:
      - The extra variables used by the module
    required: False
    type: str or dict
  user:
    description:
      - The user to execute Ansible inside kolla_toolbox with
    required: False
    type: str
  api_version:
    description:
      - The version of the API for docker-py to use when contacting Docker
    required: False
    type: str
    default: auto
  timeout:
    description:
      - The default timeout for docker-py client when contacting Docker API
    required: False
    type: int
    default: 180
author: Jeffrey Zhang
'''

EXAMPLES = '''
- hosts: controller
  tasks:
    - name: Ensure the direct absent
      kolla_toolbox:
        container_engine: docker
        module_name: file
        module_args: path=/tmp/a state=absent
    - name: Create mysql database
      kolla_toolbox:
        container_engine: docker
        module_name: mysql_db
        module_args:
          login_host: 192.168.1.10
          login_user: root
          login_password: admin
          name: testdb
    - name: Creating default user role
      kolla_toolbox:
        container_engine: docker
        module_name: os_keystone_role
        module_args:
          name: member
          auth: "{{ '{{ openstack_keystone_auth }}' }}"
        module_extra_vars:
          openstack_keystone_auth:
            auth_url: http://127.0.0.1:5000
            username: admin
            password: password
            project_name: "admin"
            domain_name: "default"
'''


JSON_REG = re.compile(r'^(?P<host>\w+) \| (?P<status>\w+)!? =>(?P<stdout>.*)$',
                      re.MULTILINE | re.DOTALL)
NON_JSON_REG = re.compile((r'^(?P<host>\w+) \| (?P<status>\w+)!? \| '
                           r'rc=(?P<exit_code>\d+) >>\n(?P<stdout>.*)\n$'),
                          re.MULTILINE | re.DOTALL)


def gen_commandline(params):
    command = ['ansible', 'localhost']
    if params.get('module_name'):
        command.extend(['-m', params.get('module_name')])
    if params.get('module_args'):
        try:
            module_args = literal_eval(params.get('module_args'))
        except SyntaxError:
            if not isinstance(params.get('module_args'), str):
                raise

            # account for string arguments
            module_args = split(params.get('module_args'))
        if isinstance(module_args, dict):
            module_args = ' '.join("{}='{}'".format(key, value)
                                   for key, value in module_args.items())
        if isinstance(module_args, list):
            module_args = ' '.join(module_args)
        command.extend(['-a', module_args])
    if params.get('module_extra_vars'):
        extra_vars = params.get('module_extra_vars')
        if isinstance(extra_vars, dict):
            extra_vars = json.dumps(extra_vars)
        command.extend(['--extra-vars', extra_vars])
    return command


def get_docker_client():
    import docker
    return docker.APIClient


def use_docker(module):
    client = get_docker_client()(
        version=module.params.get('api_version'),
        timeout=module.params.get('timeout'))
    command_line = gen_commandline(module.params)
    kolla_toolbox = client.containers(filters=dict(name='kolla_toolbox',
                                                   status='running'))
    if not kolla_toolbox:
        module.fail_json(msg='kolla_toolbox container is not running.')

    kolla_toolbox = kolla_toolbox[0]
    kwargs = {}
    if 'user' in module.params:
        kwargs['user'] = module.params['user']

    # Use the JSON output formatter, so that we can parse it.
    environment = {"ANSIBLE_STDOUT_CALLBACK": "json",
                   "ANSIBLE_LOAD_CALLBACK_PLUGINS": "True"}
    job = client.exec_create(kolla_toolbox, command_line,
                             environment=environment, **kwargs)
    json_output = client.exec_start(job)

    try:
        output = json.loads(json_output)
    except Exception:
        module.fail_json(
            msg='Can not parse the inner module output: %s' % json_output)

    # Expected format is the following:
    # {
    #   "plays": [
    #     {
    #       "tasks": [
    #         {
    #           "hosts": {
    #             "localhost": {
    #               <module result>
    #             }
    #           }
    #         }
    #       ]
    #     {
    #   ]
    # }
    try:
        ret = output['plays'][0]['tasks'][0]['hosts']['localhost']
    except (KeyError, IndexError):
        module.fail_json(
            msg='Ansible JSON output has unexpected format: %s' % output)

    # Remove Ansible's internal variables from returned fields.
    ret.pop('_ansible_no_log', None)
    return ret


def get_kolla_toolbox():
    from podman import PodmanClient

    with PodmanClient(base_url="http+unix:/run/podman/podman.sock") as client:
        for cont in client.containers.list(all=True):
            cont.reload()
            if cont.name == 'kolla_toolbox' and cont.status == 'running':
                return cont


def use_podman(module):
    from podman.errors.exceptions import APIError

    try:
        kolla_toolbox = get_kolla_toolbox()
        if not kolla_toolbox:
            module.fail_json(msg='kolla_toolbox container is not running.')

        kwargs = {}
        if 'user' in module.params:
            kwargs['user'] = module.params['user']
        environment = {"ANSIBLE_STDOUT_CALLBACK": "json",
                       "ANSIBLE_LOAD_CALLBACK_PLUGINS": "True"}
        command_line = gen_commandline(module.params)

        _, raw_output = kolla_toolbox.exec_run(
            command_line,
            environment=environment,
            tty=True,
            **kwargs
        )
    except APIError as e:
        module.fail_json(msg=f'Encountered Podman API error: {e.explanation}')

    try:
        json_output = raw_output.decode('utf-8')
        output = json.loads(json_output)
    except Exception:
        module.fail_json(
            msg='Can not parse the inner module output: %s' % json_output)

    try:
        ret = output['plays'][0]['tasks'][0]['hosts']['localhost']
    except (KeyError, IndexError):
        module.fail_json(
            msg='Ansible JSON output has unexpected format: %s' % output)

    # Remove Ansible's internal variables from returned fields.
    ret.pop('_ansible_no_log', None)

    return ret


def main():
    specs = dict(
        container_engine=dict(required=True, type='str'),
        module_name=dict(required=True, type='str'),
        module_args=dict(type='str'),
        module_extra_vars=dict(type='json'),
        api_version=dict(required=False, type='str', default='auto'),
        timeout=dict(required=False, type='int', default=180),
        user=dict(required=False, type='str'),
    )
    module = AnsibleModule(argument_spec=specs, bypass_checks=True)

    container_engine = module.params.get('container_engine').lower()
    if container_engine == 'docker':
        result = use_docker(module)
    elif container_engine == 'podman':
        result = use_podman(module)
    else:
        module.fail_json(msg='Missing or invalid container engine.')

    module.exit_json(**result)


if __name__ == "__main__":
    main()
