#!/usr/bin/python

# Copyright 2016 99cloud Inc.
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

import imp
import os
import sys

import mock
from oslotest import base
from six import StringIO


PROJECT_DIR = os.path.abspath(os.path.join(os. path.dirname(__file__), '../'))
MERGE_CONFIG_FILE = os.path.join(PROJECT_DIR,
                                 'ansible/action_plugins/merge_configs.py')

sys.modules['ansible.plugins'] = mock.MagicMock()

merge_configs = imp.load_source('merge_configs', MERGE_CONFIG_FILE)

TESTA = '''[DEFAULT]
key1 = b
       c
key2 = v1
       v2
key3 = v3
key3 = v4
key4 = v5

[b]
b_key1 = 1
b_key2 = 1
         2

[c]
c_key1 =
c_key2 = 1 2 3
         4 5 6

'''

TESTB = '''[DEFAULT]
key2 = v3
       v4
       v5
key4 = v4
key4 =

[b]
b_key2 = 2

'''

# TESTC is TESTA + TESTB
TESTC = '''[DEFAULT]
key1 = b
       c
key2 = v3
       v4
       v5
key3 = v3
key3 = v4
key4 = v4
key4 =

[b]
b_key1 = 1
b_key2 = 2

[c]
c_key1 =
c_key2 = 1 2 3
         4 5 6

'''


class OverrideConfigParserTest(base.BaseTestCase):

    def test_read_write(self):
        for ini in [TESTA, TESTB, TESTC]:
            parser = merge_configs.OverrideConfigParser()
            parser.parse(StringIO(ini))
            output = StringIO()
            parser.write(output)
            self.assertEqual(ini, output.getvalue())
            output.close()

    def test_merge(self):
        parser = merge_configs.OverrideConfigParser()
        parser.parse(StringIO(TESTA))
        parser.parse(StringIO(TESTB))
        output = StringIO()
        parser.write(output)
        self.assertEqual(TESTC, output.getvalue())
        output.close()
