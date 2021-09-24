#!/usr/bin/env python

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

from distutils.version import StrictVersion
import docker
import json
import re

from ansible.module_utils.ansible_release import __version__ as ansible_version
from ansible.module_utils.basic import AnsibleModule

from ast import literal_eval

DOCUMENTATION = '''
---
module: kolla_toolbox
short_description: >
  Module for invoking ansible module in kolla_toolbox container.
description:
  - A module targerting at invoking ansible module in kolla_toolbox
    container as used by Kolla project.
options:
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
        module_name: file
        module_args: path=/tmp/a state=absent
    - name: Create mysql database
      kolla_toolbox:
        module_name: mysql_db
        module_args:
          login_host: 192.168.1.10
          login_user: root
          login_password: admin
          name: testdb
    - name: Creating default user role
      kolla_toolbox:
        module_name: os_keystone_role
        module_args:
          name: _member_
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
        if StrictVersion(ansible_version) < StrictVersion('2.11.0'):
            module_args = params.get('module_args')
        else:
            module_args = literal_eval(params.get('module_args'))
        if isinstance(module_args, dict):
            module_args = ' '.join("{}='{}'".format(key, value)
                                   for key, value in module_args.items())
        command.extend(['-a', module_args])
    if params.get('module_extra_vars'):
        extra_vars = params.get('module_extra_vars')
        if isinstance(extra_vars, dict):
            extra_vars = json.dumps(extra_vars)
        command.extend(['--extra-vars', extra_vars])
    return command


def get_docker_client():
    return docker.APIClient


def docker_supports_environment_in_exec(client):
    docker_version = StrictVersion(client.api_version)
    return docker_version >= StrictVersion('1.25')


def main():
    specs = dict(
        module_name=dict(required=True, type='str'),
        module_args=dict(type='str'),
        module_extra_vars=dict(type='json'),
        api_version=dict(required=False, type='str', default='auto'),
        timeout=dict(required=False, type='int', default=180),
        user=dict(required=False, type='str'),
    )
    module = AnsibleModule(argument_spec=specs, bypass_checks=True)
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

    # NOTE(mgoddard): Docker 1.12 has API version 1.24, and was installed by
    # kolla-ansible bootstrap-servers on Rocky and earlier releases. This API
    # version does not have support for specifying environment variables for
    # exec jobs, which is necessary to use the Ansible JSON output formatter.
    # While we continue to support this version of Docker, fall back to the old
    # regex-based method for API version 1.24 and earlier.
    # TODO(mgoddard): Remove this conditional (keep the if) when we require
    # Docker API version 1.25+.
    if docker_supports_environment_in_exec(client):
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
    else:
        job = client.exec_create(kolla_toolbox, command_line, **kwargs)
        output = client.exec_start(job)

        for exp in [JSON_REG, NON_JSON_REG]:
            m = exp.match(output)
            if m:
                inner_output = m.groupdict().get('stdout')
                status = m.groupdict().get('status')
                break
        else:
            module.fail_json(
                msg='Can not parse the inner module output: %s' % output)

        ret = dict()
        try:
            ret = json.loads(inner_output)
        except ValueError:
            # Some modules (e.g. command) do not produce a JSON output.
            # Instead, check the status, and assume changed on success.
            ret['stdout'] = inner_output
            if status != "SUCCESS":
                ret['failed'] = True
            else:
                # No way to know whether changed - assume yes.
                ret['changed'] = True

    module.exit_json(**ret)


if __name__ == "__main__":
    main()
