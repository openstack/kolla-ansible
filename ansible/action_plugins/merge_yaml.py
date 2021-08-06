#!/usr/bin/env python

# Copyright 2015 Sam Yaple
# Copyright 2016 intel
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

import os
import shutil
import tempfile

from yaml import dump
from yaml import safe_load

from ansible import constants
from ansible import errors as ansible_errors
from ansible.plugins import action

DOCUMENTATION = '''
---
module: merge_yaml
short_description: Merge yaml-style configs
description:
     - PyYAML is used to merge several yaml files into one
options:
  dest:
    description:
      - The destination file name
    required: True
    type: str
  sources:
    description:
      - A list of files on the destination node to merge together
    default: None
    required: True
    type: str
  extend_lists:
    description:
      - For a given key referencing a list, this determines whether
        the list items should be combined with the items in another
        document if an equivalent key is found. An equivalent key
        has the same parents and value as the first. The default
        behaviour is to replace existing entries i.e if you have
        two yaml documents that both define a list with an equivalent
        key, the value from the document that appears later in the
        list of sources will replace the value that appeared in the
        earlier one.
    default: False
    required: False
    type: bool
author: Sean Mooney
'''

EXAMPLES = '''
Merge multiple yaml files:

- hosts: localhost
  tasks:
    - name: Merge yaml files
      merge_yaml:
        sources:
          - "/tmp/default.yml"
          - "/tmp/override.yml"
        dest:
          - "/tmp/out.yml"
'''


class ActionModule(action.ActionBase):

    TRANSFERS_FILES = True

    def read_config(self, source):
        result = None
        # Only use config if present
        if os.access(source, os.R_OK):
            with open(source, 'r') as f:
                template_data = f.read()

            # set search path to mimic 'template' module behavior
            searchpath = [
                self._loader._basedir,
                os.path.join(self._loader._basedir, 'templates'),
                os.path.dirname(source),
            ]
            self._templar.environment.loader.searchpath = searchpath

            template_data = self._templar.template(template_data)
            result = safe_load(template_data)
        return result or {}

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()
        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # not used

        # save template args.
        extra_vars = self._task.args.get('vars', list())
        old_vars = self._templar._available_variables

        temp_vars = task_vars.copy()
        temp_vars.update(extra_vars)
        self._templar.available_variables = temp_vars

        output = {}
        sources = self._task.args.get('sources', None)
        extend_lists = self._task.args.get('extend_lists', False)
        if not isinstance(sources, list):
            sources = [sources]
        for source in sources:
            Utils.update_nested_conf(
                output, self.read_config(source), extend_lists)

        # restore original vars
        self._templar.available_variables = old_vars

        local_tempdir = tempfile.mkdtemp(dir=constants.DEFAULT_LOCAL_TMP)

        try:
            result_file = os.path.join(local_tempdir, 'source')
            with open(result_file, 'w') as f:
                f.write(dump(output, default_flow_style=False))

            new_task = self._task.copy()
            new_task.args.pop('sources', None)
            new_task.args.pop('extend_lists', None)
            new_task.args.update(
                dict(
                    src=result_file
                )
            )

            copy_action = self._shared_loader_obj.action_loader.get(
                'copy',
                task=new_task,
                connection=self._connection,
                play_context=self._play_context,
                loader=self._loader,
                templar=self._templar,
                shared_loader_obj=self._shared_loader_obj)
            result.update(copy_action.run(task_vars=task_vars))
        finally:
            shutil.rmtree(local_tempdir)
        return result


class Utils(object):
    @staticmethod
    def update_nested_conf(conf, update, extend_lists=False):
        for k, v in update.items():
            if isinstance(v, dict):
                conf[k] = Utils.update_nested_conf(
                    conf.get(k, {}), v, extend_lists)
            elif k in conf and isinstance(conf[k], list) and extend_lists:
                if not isinstance(v, list):
                    errmsg = (
                        "Failure merging key `%(key)s` in dictionary "
                        "`%(dictionary)s`. Expecting a list, but received: "
                        "`%(value)s`, which is of type: `%(type)s`" % {
                            "key": k, "dictionary": conf,
                            "value": v, "type": type(v)}
                    )
                    raise ansible_errors.AnsibleModuleError(errmsg)
                conf[k].extend(v)
            else:
                conf[k] = v
        return conf
