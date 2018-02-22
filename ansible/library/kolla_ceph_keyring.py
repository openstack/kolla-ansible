#!/usr/bin/env python

# Copyright 2018 99cloud
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
import subprocess  # nosec


DOCUMENTATION = '''
---
module: kolla_ceph_keyring
short_description: >
  Module for update ceph client keyring caps in kolla.
description:
  - A module used to update ceph client keyring caps in kolla.
options:
  name:
    description:
      - the client name in ceph
    required: True
    type: str
  container_name:
    description:
      - the ceph mon container name
    required: True
    default: ceph_mon
    type: str
  caps:
    description:
      - the ceph auth caps
    required: True
    type: dict
author: Jeffrey Zhang
'''

EXAMPLES = '''
- name: configure admin client caps
  kolla_ceph_keyring:
    name: client.admin
    container_name: ceph_mon
    caps:
      mds: 'allow'
      mon: 'allow *'
      osd: 'allow *'
      mgr: 'allow *'
'''


class CephKeyring(object):
    def __init__(self, name, caps, container_name='ceph_mon'):
        self.name = name
        self.caps = caps
        self.container_name = container_name
        self.changed = False
        self.message = None

    def _run(self, cmd):
        _prefix = ['docker', 'exec', self.container_name]
        cmd = _prefix + cmd
        proc = subprocess.Popen(cmd,  # nosec
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        retcode = proc.poll()
        if retcode != 0:
            output = 'stdout: "%s", stderr: "%s"' % (stdout, stderr)
            raise subprocess.CalledProcessError(retcode, cmd, output)
        return stdout

    def _format_caps(self):
        caps = []
        for obj in sorted(self.caps):
            caps.extend([obj, self.caps[obj]])
        return caps

    def parse_stdout(self, stdout):
        keyring = json.loads(stdout)
        # there should be only one element
        return keyring[0]

    def ensure_keyring(self):
        try:
            stdout = self.get_keyring()
        except subprocess.CalledProcessError:
            # keyring doesn't exsit, try to create it
            stdout = self.create_keyring()
            self.changed = True
            self.message = 'ceph keyring for %s is created' % self.name
        keyring = self.parse_stdout(stdout)
        if keyring['caps'] != self.caps:
            self.update_caps()
            stdout = self.get_keyring()
            keyring = self.parse_stdout(stdout)
            self.changed = True
            self.message = 'ceph keyring for %s is updated' % self.name
        self.keyring = keyring
        return self.keyring

    def get_keyring(self):
        ceph_cmd = ['ceph', '--format', 'json', 'auth', 'get', self.name]
        return self._run(ceph_cmd)

    def update_caps(self):
        ceph_cmd = ['ceph', '--format', 'json', 'auth', 'caps', self.name]
        caps = self._format_caps()
        ceph_cmd.extend(caps)
        self._run(ceph_cmd)

    def create_keyring(self):
        ceph_cmd = ['ceph', '--format', 'json', 'auth',
                    'get-or-create', self.name]
        caps = self._format_caps()
        ceph_cmd.extend(caps)
        return self._run(ceph_cmd)


def main():
    specs = dict(
        name=dict(type='str', required=True),
        container_name=dict(type='str', default='ceph_mon'),
        caps=dict(type='dict', required=True)
    )
    module = AnsibleModule(argument_spec=specs)  # noqa
    params = module.params
    ceph_keyring = CephKeyring(params['name'],
                               params['caps'],
                               params['container_name'])
    try:
        keyring = ceph_keyring.ensure_keyring()
        module.exit_json(changed=ceph_keyring.changed,
                         keyring=keyring,
                         message=ceph_keyring.message)
    except subprocess.CalledProcessError as ex:
        msg = ('Failed to call command: %s returncode: %s output: %s' %
               (ex.cmd, ex.returncode, ex.output))
        module.fail_json(msg=msg)


from ansible.module_utils.basic import *  # noqa
if __name__ == "__main__":
    main()
