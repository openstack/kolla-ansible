#!/usr/bin/env python3

# Copyright 2020 StackHPC Ltd.
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

"""
Original license:
@author Gerard van Helden <drm@melp.nl>
@license DBAD, see <http://www.dbad-license.org/>
@url https://github.com/drm/jinja2-lint
Simple j2 linter, useful for checking jinja2 template syntax

Adapted for OpenStack Kolla/Kolla-Ansible purposes
"""

from ansible.plugins.filter.core import get_encrypted_password
from ansible.plugins.filter.core import to_json
from functools import reduce
from jinja2 import BaseLoader
from jinja2 import Environment
from jinja2 import exceptions
from jinja2 import TemplateNotFound
from kolla_ansible import kolla_address
from kolla_ansible import put_address_in_context
import os.path
try:
    from ansible_collections.ansible.utils.plugins.filter import ipwrap
except ImportError:
    from ansible_collections.ansible.netcommon.plugins.filter import ipwrap


class AbsolutePathLoader(BaseLoader):
    def get_source(self, environment, template):
        if not os.path.exists(template):
            raise TemplateNotFound(template)
        mtime = os.path.getmtime(template)
        with open(template) as file:
            source = file.read()
        return source, template, lambda: mtime == os.path.getmtime(template)


def check(template, out, err, env=Environment(loader=AbsolutePathLoader(),
          autoescape=True)):
    try:
        env.filters['basename'] = os.path.basename
        env.filters['bool'] = bool
        env.filters['hash'] = hash
        env.filters['to_json'] = to_json
        # NOTE(wszumski): password_hash is mapped to the function:
        # get_encrypted_password in ansible.filters.core.
        env.filters['password_hash'] = get_encrypted_password
        env.filters['kolla_address'] = kolla_address
        env.filters['put_address_in_context'] = put_address_in_context
        env.filters['ipwrap'] = ipwrap
        env.get_template(template)
        out.write("%s: Syntax OK\n" % template)
        return 0
    except TemplateNotFound:
        err.write("%s: File not found\n" % template)
        return 2
    except exceptions.TemplateSyntaxError as ex:
        err.write("%s: Syntax check failed: %s in %s at %d\n"
                  % (template, ex.message, ex.filename, ex.lineno))
        return 1


def main(**kwargs):
    import sys
    try:
        sys.exit(reduce(lambda r, fn: r +
                        check(fn, sys.stdout, sys.stderr, **kwargs),
                        sys.argv[1:], 0))
    except IndexError:
        sys.stdout.write("Usage: j2lint.py filename [filename ...]\n")


if __name__ == "__main__":
    main()
