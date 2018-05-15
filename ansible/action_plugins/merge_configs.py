#!/usr/bin/env python

# Copyright 2015 Sam Yaple
# Copyright 2017 99Cloud Inc.
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


import collections
import inspect
import os
import shutil
import tempfile

from ansible import constants
from ansible.plugins import action
from six import StringIO

from oslo_config import iniparser

_ORPHAN_SECTION = 'TEMPORARY_ORPHAN_VARIABLE_SECTION'


class OverrideConfigParser(iniparser.BaseParser):

    def __init__(self):
        self._cur_sections = collections.OrderedDict()
        self._sections = collections.OrderedDict()
        self._cur_section = None

    def assignment(self, key, value):
        if self._cur_section is None:
            self.new_section(_ORPHAN_SECTION)
        cur_value = self._cur_section.get(key)
        if len(value) == 1 and value[0] == '':
            value = []
        if not cur_value:
            self._cur_section[key] = [value]
        else:
            self._cur_section[key].append(value)

    def parse(self, lineiter):
        self._cur_sections = collections.OrderedDict()
        self._cur_section = None
        super(OverrideConfigParser, self).parse(lineiter)

        # merge _cur_sections into _sections
        for section, values in self._cur_sections.items():
            if section not in self._sections:
                self._sections[section] = collections.OrderedDict()
            for key, value in values.items():
                self._sections[section][key] = value

    def new_section(self, section):
        cur_section = self._cur_sections.get(section)
        if not cur_section:
            cur_section = collections.OrderedDict()
            self._cur_sections[section] = cur_section
        self._cur_section = cur_section
        return cur_section

    def write(self, fp):
        def write_key_value(key, values):
            for v in values:
                if not v:
                    fp.write('{} =\n'.format(key))
                for index, value in enumerate(v):
                    if index == 0:
                        fp.write('{} = {}\n'.format(key, value))
                    else:
                        fp.write('{}   {}\n'.format(len(key)*' ', value))

        def write_section(section):
            for key, values in section.items():
                write_key_value(key, values)

        for section in self._sections:
            if section != _ORPHAN_SECTION:
                fp.write('[{}]\n'.format(section))
            write_section(self._sections[section])
            fp.write('\n')


class ActionModule(action.ActionBase):

    TRANSFERS_FILES = True

    def read_config(self, source, config):
        # Only use config if present
        if os.access(source, os.R_OK):
            with open(source, 'r') as f:
                template_data = f.read()
            result = self._templar.template(template_data)
            fakefile = StringIO(result)
            config.parse(fakefile)
            fakefile.close()

    def run(self, tmp=None, task_vars=None):

        result = super(ActionModule, self).run(tmp, task_vars)

        # NOTE(jeffrey4l): Ansible 2.1 add a remote_user param to the
        # _make_tmp_path function.  inspect the number of the args here. In
        # this way, ansible 2.0 and ansible 2.1 are both supported
        make_tmp_path_args = inspect.getargspec(self._make_tmp_path)[0]
        if not tmp and len(make_tmp_path_args) == 1:
            tmp = self._make_tmp_path()
        if not tmp and len(make_tmp_path_args) == 2:
            remote_user = (task_vars.get('ansible_user')
                           or self._play_context.remote_user)
            tmp = self._make_tmp_path(remote_user)

        sources = self._task.args.get('sources', None)

        if not isinstance(sources, list):
            sources = [sources]

        config = OverrideConfigParser()

        for source in sources:
            self.read_config(source, config)

        # Dump configparser to string via an emulated file

        fakefile = StringIO()
        config.write(fakefile)
        full_source = fakefile.getvalue()
        fakefile.close()

        local_tempdir = tempfile.mkdtemp(dir=constants.DEFAULT_LOCAL_TMP)

        try:
            result_file = os.path.join(local_tempdir, 'source')
            with open(result_file, 'wb') as f:
                f.write(full_source)

            new_task = self._task.copy()
            new_task.args.pop('sources', None)

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
