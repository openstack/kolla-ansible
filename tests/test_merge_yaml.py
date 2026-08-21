#!/usr/bin/env python

# Copyright 2018 StackHPC Ltd.
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

from importlib.machinery import SourceFileLoader
import os
import tempfile

from ansible.errors import AnsibleModuleError
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar
from oslotest import base

PROJECT_DIR = os.path.abspath(os.path.join(os. path.dirname(__file__), '../'))
MERGE_YAML_FILE = os.path.join(PROJECT_DIR,
                               'ansible/action_plugins/merge_yaml.py')
merge_yaml = SourceFileLoader('merge_yaml', MERGE_YAML_FILE).load_module()


class MergeYamlConfigTest(base.BaseTestCase):

    def test_merge_no_update(self):
        initial_conf = {
            'foo': 'bar',
            'egg': 'spam'
        }
        actual = merge_yaml.Utils.update_nested_conf(initial_conf, {})
        expected = {
            'foo': 'bar',
            'egg': 'spam'
        }
        self.assertDictEqual(actual, expected)

    def test_merge_flat_update_key(self):
        initial_conf = {
            'foo': 'bar',
            'egg': 'spam'
        }
        actual = merge_yaml.Utils.update_nested_conf(
            initial_conf, {'egg': 'ham'})
        expected = {
            'foo': 'bar',
            'egg': 'ham'
        }
        self.assertDictEqual(actual, expected)

    def test_merge_flat_new_key(self):
        initial_conf = {
            'foo': 'bar',
            'egg': 'spam'
        }
        actual = merge_yaml.Utils.update_nested_conf(
            initial_conf, {'spam': 'ham'})
        expected = {
            'foo': 'bar',
            'egg': 'spam',
            'spam': 'ham'
        }
        self.assertDictEqual(actual, expected)

    def test_merge_nested_update_key(self):
        initial_conf = {
            'foo': {
                'a': 'b',
            },
            'bar': {
                'a': False,
                'b': 'INFO'
            }
        }
        actual = merge_yaml.Utils.update_nested_conf(
            initial_conf, {'bar': {'a': True}})
        expected = {
            'foo': {
                'a': 'b',
            },
            'bar': {
                'a': True,
                'b': 'INFO'
            }
        }
        self.assertDictEqual(actual, expected)

    def test_merge_nested_new_key(self):
        initial_conf = {
            'foo': {
                'a': 'b',
                'c': 30
            }
        }
        actual = merge_yaml.Utils.update_nested_conf(
            initial_conf, {'egg': {'spam': 10}})
        expected = {
            'foo': {
                'a': 'b',
                'c': 30,
            },
            'egg': {
                'spam': 10,
            }
        }
        self.assertDictEqual(actual, expected)

    def test_merge_nested_new_nested_key(self):
        initial_conf = {
            'foo': {
                'a': 'b',
                'c': 30
            }
        }
        actual = merge_yaml.Utils.update_nested_conf(
            initial_conf, {'foo': {'spam': 10}})
        expected = {
            'foo': {
                'a': 'b',
                'c': 30,
                'spam': 10,
            }
        }
        self.assertDictEqual(actual, expected)

    def test_merge_nested_extend_lists(self):
        initial_conf = {
            'level0': {
                'level1': {
                    "mylist": ["one", "two"]
                },
            }
        }

        extension = {
            'level0': {
                'level1': {
                    "mylist": ["three"]
                },
            }
        }

        actual = merge_yaml.Utils.update_nested_conf(
            initial_conf, extension, extend_lists=True)
        expected = {
            'level0': {
                'level1': {
                    "mylist": ["one", "two", "three"]
                },
            }
        }
        self.assertDictEqual(actual, expected)

    def test_merge_nested_extend_lists_mismatch_types(self):
        initial_conf = {
            'level0': {
                'level1': {
                    "mylist": ["one", "two"]
                },
            }
        }

        extension = {
            'level0': {
                'level1': {
                    "mylist": "three"
                },
            }
        }
        with self.assertRaisesRegex(AnsibleModuleError, "Failure merging key"):
            merge_yaml.Utils.update_nested_conf(
                initial_conf, extension, extend_lists=True)

    def test_read_config_lstrip_blocks(self):
        # An indented Jinja2 block tag on its own line must not leak its
        # leading whitespace into the following line, or the resulting
        # YAML indentation becomes inconsistent with its siblings.
        content = (
            "foo:\n"
            "  bar: baz\n"
            "  {% if true %}\n"
            "  extra: value\n"
            "  {% endif %}\n"
            "  qux: quux\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, 'source.yml')
            with open(source, 'w') as f:
                f.write(content)

            loader = DataLoader()
            loader.set_basedir(tmpdir)
            action = object.__new__(merge_yaml.ActionModule)
            action._loader = loader
            action._templar = Templar(loader=loader)

            result = action.read_config(source)

        self.assertEqual(
            {'foo': {'bar': 'baz', 'extra': 'value', 'qux': 'quux'}},
            result)
