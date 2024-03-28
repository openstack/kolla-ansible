#!/usr/bin/env python

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

from importlib.machinery import SourceFileLoader
import os

from io import StringIO
from oslotest import base


PROJECT_DIR = os.path.abspath(os.path.join(os. path.dirname(__file__), '../'))
MERGE_CONFIG_FILE = os.path.join(PROJECT_DIR,
                                 'ansible/action_plugins/merge_configs.py')


merge_configs = SourceFileLoader('merge_configs',
                                 MERGE_CONFIG_FILE).load_module()

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

TESTA_NO_SECTIONS = '''key1 = a
key2 = b

'''

TESTB_NO_SECTIONS = '''key3 = c

'''

# TESTA_NO_SECTIONS and TESTB_NO_SECTIONS combined
TESTC_NO_SECTIONS = '''key1 = a
key2 = b
key3 = c

'''

TESTA_NO_DEFAULT_SECTION = '''key1 = a
key2 = b

[a]
key1 = not_a

[b]
key3 = not_c

'''

TESTB_NO_DEFAULT_SECTION = '''key3 = c

[b]
key2 = not_b
key3 = override

'''

# TESTA_NO_DEFAULT_SECTION and TESTB_NO_DEFAULT_SECTION combined
TESTC_NO_DEFAULT_SECTION = '''key1 = a
key2 = b
key3 = c

[a]
key1 = not_a

[b]
key3 = override
key2 = not_b

'''

# TESTC_NO_WHITESPACE is TESTA + TESTB without whitespace around equal signs
TESTC_NO_WHITESPACE = '''[DEFAULT]
key1=b
     c
key2=v3
     v4
     v5
key3=v3
key3=v4
key4=v4
key4=

[b]
b_key1=1
b_key2=2

[c]
c_key1=
c_key2=1 2 3
       4 5 6

'''


class OverrideConfigParserTest(base.BaseTestCase):

    def test_read_write(self):
        for ini in [TESTA,
                    TESTB,
                    TESTC,
                    TESTA_NO_SECTIONS,
                    TESTB_NO_SECTIONS,
                    TESTC_NO_SECTIONS,
                    TESTA_NO_DEFAULT_SECTION,
                    TESTB_NO_DEFAULT_SECTION,
                    TESTC_NO_DEFAULT_SECTION]:
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

    def test_merge_no_sections(self):
        parser = merge_configs.OverrideConfigParser()
        parser.parse(StringIO(TESTA_NO_SECTIONS))
        parser.parse(StringIO(TESTB_NO_SECTIONS))
        output = StringIO()
        parser.write(output)
        self.assertEqual(TESTC_NO_SECTIONS, output.getvalue())
        output.close()

    def test_merge_no_default_section(self):
        parser = merge_configs.OverrideConfigParser()
        parser.parse(StringIO(TESTA_NO_DEFAULT_SECTION))
        parser.parse(StringIO(TESTB_NO_DEFAULT_SECTION))
        output = StringIO()
        parser.write(output)
        self.assertEqual(TESTC_NO_DEFAULT_SECTION, output.getvalue())
        output.close()

    def test_merge_no_whitespace(self):
        parser = merge_configs.OverrideConfigParser(whitespace=False)
        parser.parse(StringIO(TESTA))
        parser.parse(StringIO(TESTB))
        output = StringIO()
        parser.write(output)
        self.assertEqual(TESTC_NO_WHITESPACE, output.getvalue())
        output.close()
