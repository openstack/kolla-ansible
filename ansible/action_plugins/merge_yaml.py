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

import inspect
import os
import shutil
import tempfile

from yaml import dump
from yaml import safe_load
try:
    from yaml import CDumper as Dumper  # noqa: F401
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper  # noqa: F401
    from yaml import Loader  # noqa: F401


from ansible import constants
from ansible.plugins import action


class ActionModule(action.ActionBase):

    TRANSFERS_FILES = True

    def read_config(self, source):
        result = None
        # Only use config if present
        if os.access(source, os.R_OK):
            with open(source, 'r') as f:
                template_data = f.read()
            template_data = self._templar.template(template_data)
            result = safe_load(template_data)
        return result or {}

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()
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
        # save template args.
        extra_vars = self._task.args.get('vars', list())
        old_vars = self._templar._available_variables

        temp_vars = task_vars.copy()
        temp_vars.update(extra_vars)
        self._templar.set_available_variables(temp_vars)

        output = {}
        sources = self._task.args.get('sources', None)
        if not isinstance(sources, list):
            sources = [sources]
        for source in sources:
            output.update(self.read_config(source))

        # restore original vars
        self._templar.set_available_variables(old_vars)

        local_tempdir = tempfile.mkdtemp(dir=constants.DEFAULT_LOCAL_TMP)

        try:
            result_file = os.path.join(local_tempdir, 'source')
            with open(result_file, 'wb') as f:
                f.write(dump(output, default_flow_style=False))

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
