#!/usr/bin/env python

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
import fnmatch
import json
import logging
import os
import re
import sys

import jinja2
import yaml


from kolla_ansible.put_address_in_context import put_address_in_context


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

NEWLINE_EOF_INCLUDE_PATTERNS = ['*.j2', '*.yml', '*.py', '*.sh']
NEWLINE_EOF_EXCLUDE_PATTERNS = ['.tox', '.testrepository', '.git']

# Render json file by using jinja2 template is OK
JSON_J2_INCLUDE_PATTERNS = ['*.json.j2', '*.json']
JSON_J2_EXCLUDE_PATTERNS = ['.tox', '.testrepository', '.git']

YAML_INCLUDE_PATTERNS = ['*.yml']
YAML_EXCLUDE_PATTERNS = ['.tox', '.testrepository', '.git',
                         'defaults', 'templates', 'vars']

KOLLA_NETWORKS = [
    'api',
    'storage',
    'migration',
    'tunnel',
    'octavia_network',
    'bifrost_network',
    'dns',  # designate
]

logging.basicConfig()
LOG = logging.getLogger(__name__)


def check_newline_eof():
    includes = r'|'.join([fnmatch.translate(x)
                          for x in NEWLINE_EOF_INCLUDE_PATTERNS])
    excludes = r'|'.join([fnmatch.translate(x)
                          for x in NEWLINE_EOF_EXCLUDE_PATTERNS])
    return_code = 0

    def has_newline_eof(path):
        with open(path, 'r') as f:
            data = f.read()
            if data and data[-1] != '\n':
                LOG.error('%s file error: no newline at end of file', path)
                return False
        return True

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if not re.match(excludes, d)]
        for f in files:
            if not re.match(excludes, f) and re.match(includes, f):
                if not has_newline_eof(os.path.join(root, f)):
                    return_code = 1
    return return_code


def check_json_j2():
    includes = r'|'.join([fnmatch.translate(x)
                          for x in JSON_J2_INCLUDE_PATTERNS])
    excludes = r'|'.join([fnmatch.translate(x)
                          for x in JSON_J2_EXCLUDE_PATTERNS])
    return_code = 0

    def bool_filter(value):
        return True

    def basename_filter(text):
        return text.split('\\')[-1]

    def kolla_address_filter_mock(network_name, hostname=None):
        # no validation is possible for the hostname

        if network_name not in KOLLA_NETWORKS:
            raise ValueError("{network_name} not in KOLLA_NETWORKS"
                             .format(network_name=network_name))

        return "127.0.0.1"

    # Mock ansible hostvars variable, which is a nested dict
    def hostvars():
        return collections.defaultdict(hostvars)

    # Mock Ansible groups variable, which is a dict of lists.
    def groups():
        return collections.defaultdict(list)

    def validate_json_j2(root, filename):
        env = jinja2.Environment(  # nosec: not used to render HTML
            loader=jinja2.FileSystemLoader(root))
        env.filters['bool'] = bool_filter
        env.filters['basename'] = basename_filter
        env.filters['kolla_address'] = kolla_address_filter_mock
        env.filters['put_address_in_context'] = \
            put_address_in_context
        template = env.get_template(filename)
        # Mock ansible variables.
        context = {
            'hostvars': hostvars(),
            'groups': groups(),
            'inventory_hostname': 'hostname',
            'api_interface_address': '',
            'kolla_internal_fqdn': '',
            'octavia_provider_drivers': '',
            'ovn_sb_db_relay_active_inactivity_probe': 120000,
            'ovn_sb_db_relay_passive_inactivity_probe': 60000,
            'ovn_sb_db_relay_max_backoff': 60000,
            'rabbitmq_ha_replica_count': 2,
            'rabbitmq_message_ttl_ms': 600000,
            'rabbitmq_queue_expiry_ms': 3600000,

        }
        data = template.render(**context)
        json.loads(data)
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if not re.match(excludes, d)]
        for filename in files:
            if not re.match(excludes, filename) and \
                    re.match(includes, filename):
                fullpath = os.path.join(root, filename)
                try:
                    validate_json_j2(root, filename)
                except (ValueError, jinja2.exceptions.TemplateError):
                    return_code = 1
                    LOG.exception('%s file error', fullpath)
    return return_code


def check_task_contents():
    """All tasks that use Docker should have 'become: true'."""
    includes = r'|'.join([fnmatch.translate(x)
                          for x in YAML_INCLUDE_PATTERNS])
    excludes = r'|'.join([fnmatch.translate(x)
                          for x in YAML_EXCLUDE_PATTERNS])
    roles_path = os.path.join(PROJECT_ROOT, 'ansible', 'roles')
    return_code = 0
    for root, dirs, files in os.walk(roles_path):
        dirs[:] = [d for d in dirs if not re.match(excludes, d)]
        for filename in files:
            if not re.match(excludes, filename) and \
                    re.match(includes, filename):
                fullpath = os.path.join(root, filename)
                with open(fullpath) as fp:
                    tasks = yaml.safe_load(fp)
                tasks = tasks or []
                for task in tasks:
                    if task.get('block'):
                        block = task
                        for task in task['block']:
                            if check_container_become(fullpath, task, block):
                                return_code = 1
                    else:
                        if check_container_become(fullpath, task):
                            return_code = 1

    return return_code


def check_container_become(fullpath, task, block=''):

    ce_modules = ('kolla_container', 'kolla_container_facts', 'kolla_toolbox')
    cmd_modules = ('command', 'shell')
    return_code = 0

    for module in ce_modules:
        if (module in task and not task.get('become') and
                not block.get('become')):
            return_code = 1
            LOG.error("Use of %s module without become in "
                      "task %s in %s",
                      module, task['name'], fullpath)
    for module in cmd_modules:
        ce_without_become = False
        if (module in task and not task.get('become')):
            if (isinstance(task[module], str) and
                    (task[module].startswith('docker') or
                     task[module].startswith('podman')) and
                    not block.get('become')):
                ce_without_become = True
            if (isinstance(task[module], dict) and
                    (task[module]['cmd'].startswith('docker') or
                     task[module]['cmd'].startswith('podman')) and
                    not block.get('become')):
                ce_without_become = True
            if ce_without_become:
                return_code = 1
                LOG.error("Use of container engine in %s "
                          "module without "
                          "become in task %s in %s block %s",
                          module, task['name'], fullpath, block)
    return return_code


def main():
    checks = (
        check_newline_eof,
        check_json_j2,
        check_task_contents,
    )
    return sum([check() for check in checks])


if __name__ == "__main__":
    sys.exit(main())
