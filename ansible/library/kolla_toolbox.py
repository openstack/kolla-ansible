#!/usr/bin/python

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


import docker
import json
import re


JSON_REG = re.compile('^(?P<host>\w+) \| (?P<status>\w+)!? =>(?P<stdout>.*)$',
                      re.MULTILINE | re.DOTALL)
NON_JSON_REG = re.compile(('^(?P<host>\w+) \| (?P<status>\w+)!? \| '
                           'rc=(?P<exit_code>\d+) >>\n(?P<stdout>.*)\n$'),
                          re.MULTILINE | re.DOTALL)


def gen_commandline(params):
    command = ['ansible', 'localhost']
    if params.get('module_name'):
        command.extend(['-m', params.get('module_name')])
    if params.get('module_args'):
        module_args = params.get('module_args')
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


def main():
    specs = dict(
        module_name=dict(type='str'),
        module_args=dict(type='str'),
        module_extra_vars=dict(type='json')
        )
    module = AnsibleModule(argument_spec=specs, bypass_checks=True)
    client = docker.Client()
    command_line = gen_commandline(module.params)
    kolla_toolbox = client.containers(filters=dict(name='kolla_toolbox',
                                                   status='running'))
    if not kolla_toolbox:
        module.fail_json(msg='kolla_toolbox container is not running.')

    kolla_toolbox = kolla_toolbox[0]
    job = client.exec_create(kolla_toolbox, command_line)
    output = client.exec_start(job)

    for exp in [JSON_REG, NON_JSON_REG]:
        m = exp.match(output)
        if m:
            inner_output = m.groupdict().get('stdout')
            break
    else:
        module.fail_json(
            msg='Can not parse the inner module output: %s' % output)

    ret = dict()
    try:
        ret = json.loads(inner_output)
    except ValueError:
        ret['stdout'] = inner_output

    module.exit_json(**ret)


from ansible.module_utils.basic import *  # noqa
if __name__ == "__main__":
    main()
