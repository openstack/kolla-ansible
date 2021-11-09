# Copyright (c) 2019 StackHPC Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import unittest

import jinja2
import os

from kolla_ansible import nova_filters as filters


class TestFilters(unittest.TestCase):

    def _test_extract_cell(self, test_data, cell_name):
        nova_manage_output = {}
        with open(test_data, 'r') as f:
            nova_manage_output['stdout_lines'] = f.readlines()
        return filters.extract_cell(nova_manage_output, cell_name)

    def test_extract_with_no_name(self):
        test_data = os.path.join(os.path.dirname(
            __file__), 'data', 'nova_manage_cli_output_multiple_cells')
        actual = self._test_extract_cell(test_data, '')
        expected = {'cell_name': None,
                    'cell_uuid': '68a3f49e-27ec-422f-9e2e-2a4e5dc8291b',
                    'cell_message_queue': 'rabbit://openstack:94uCcArVNXEJnhhj4JAAAMI432h5j3k2bb3bbjkB@172.28.128.30:5672',  # noqa
                    'cell_database': 'mysql+pymysql://nova:1nhsVDLWjsFSoCsda453bJBsdsbjkabf77sadsdD@172.28.128.252:3305/nova',  # noqa
                    'cell_disabled': 'False'}
        self.assertDictEqual(expected, actual)

    def test_extract_cell0001(self):
        test_data = os.path.join(os.path.dirname(
            __file__), 'data', 'nova_manage_cli_output_multiple_cells')
        actual = self._test_extract_cell(test_data, 'cell0001')
        expected = {'cell_name': 'cell0001',
                    'cell_uuid': '5af50f3f-82ed-47b2-9de8-7dd4eafa7648',
                    'cell_message_queue': 'rabbit://openstack:0flZc3qqwczsisbaT94uCcArVNXEJnhhj4JAAAMI@172.28.128.32:5673/nova_cell0001',  # noqa
                    'cell_database': 'mysql+pymysql://nova:mpyerUgpbQeXjaDV1nhsVDLWjsFSoCss6dHCXK7G@172.28.128.252:3305/nova_cell0001',  # noqa
                    'cell_disabled': 'False'}
        self.assertDictEqual(expected, actual)

    def test_extract_cell0002(self):
        test_data = os.path.join(os.path.dirname(
            __file__), 'data', 'nova_manage_cli_output_multiple_cells')
        actual = self._test_extract_cell(test_data, 'cell0002')
        expected = {'cell_name': 'cell0002',
                    'cell_uuid': '087697bb-bfc2-471d-befb-0c0fcc7630e4',
                    'cell_message_queue': 'rabbit://openstack:d9LaCxGrQX9Lla9aMZcS7fQ5xLH8S5HwHFrl6jdJ@172.28.128.31:5672/nova_cell0002',  # noqa
                    'cell_database': 'mysql+pymysql://nova:Dj3f3l4yv2SuhbsJyv3ahGIwUMa9TKchw6EXtQfp@172.28.128.253:3306/nova_cell0002',  # noqa
                    'cell_disabled': 'True'}
        self.assertDictEqual(expected, actual)

    def test_extract_missing_cell(self):
        test_data = os.path.join(os.path.dirname(
            __file__), 'data', 'nova_manage_cli_output_multiple_cells')
        actual = self._test_extract_cell(test_data, 'cell0003')
        self.assertIsNone(actual)

    def test_extract_duplicate_cell(self):
        test_data = os.path.join(os.path.dirname(
            __file__), 'data', 'nova_manage_cli_output_duplicate_cells')
        self.assertRaisesRegex(jinja2.TemplateRuntimeError, 'duplicates',
                               self._test_extract_cell, test_data, 'cell0001')

    def test_namespace_haproxy_for_cell_with_empty_name(self):
        example_services = {
            'nova-novncproxy': {
                'group': 'some_group',
                'enabled': True,
                'haproxy': {
                    'nova_novncproxy': {
                        'enabled': True,
                        'mode': 'http',
                        'external': False,
                        'port': '1232',
                        'listen_port': '1233',
                        'backend_http_extra': ['timeout tunnel 1h'],
                    },
                    'nova_novncproxy_external': {
                        'enabled': True,
                        'mode': 'http',
                        'external': True,
                        'port': '1234',
                        'listen_port': '1235',
                        'backend_http_extra': ['timeout tunnel 1h'],
                    }
                }
            }
        }
        actual = filters.namespace_haproxy_for_cell(example_services, '')
        # No change
        self.assertDictEqual(example_services, actual)

    def test_namespace_haproxy_for_cell_with_single_proxy(self):
        example_services = {
            'nova-novncproxy': {
                'group': 'some_group',
                'enabled': True,
                'haproxy': {
                    'nova_novncproxy': {
                        'enabled': True,
                        'mode': 'http',
                        'external': False,
                        'port': '1232',
                        'listen_port': '1233',
                        'backend_http_extra': ['timeout tunnel 1h'],
                    },
                    'nova_novncproxy_external': {
                        'enabled': True,
                        'mode': 'http',
                        'external': True,
                        'port': '1234',
                        'listen_port': '1235',
                        'backend_http_extra': ['timeout tunnel 1h'],
                    }
                }
            }
        }
        actual = filters.namespace_haproxy_for_cell(
            example_services, 'cell0001')
        expected = {
            'nova-novncproxy_cell0001': {
                'group': 'some_group',
                'enabled': True,
                'haproxy': {
                    'nova_novncproxy_cell0001': {
                        'enabled': True,
                        'mode': 'http',
                        'external': False,
                        'port': '1232',
                        'listen_port': '1233',
                        'backend_http_extra': ['timeout tunnel 1h'],
                    },
                    'nova_novncproxy_external_cell0001': {
                        'enabled': True,
                        'mode': 'http',
                        'external': True,
                        'port': '1234',
                        'listen_port': '1235',
                        'backend_http_extra': ['timeout tunnel 1h'],
                    }
                }
            }
        }
        self.assertDictEqual(expected, actual)

    def test_namespace_haproxy_for_cell_with_multiple_proxies(self):
        example_services = {
            'nova-novncproxy': {
                'haproxy': {
                    'nova_novncproxy': {},
                    'nova_novncproxy_external': {}
                }
            },
            'nova-spicehtml5proxy': {
                'haproxy': {
                    'nova_spicehtml5proxy': {},
                    'nova_spicehtml5proxy_external': {}
                }
            }
        }
        actual = filters.namespace_haproxy_for_cell(
            example_services, 'cell0002')
        expected = {
            'nova-novncproxy_cell0002': {
                'haproxy': {
                    'nova_novncproxy_cell0002': {},
                    'nova_novncproxy_external_cell0002': {}
                }
            },
            'nova-spicehtml5proxy_cell0002': {
                'haproxy': {
                    'nova_spicehtml5proxy_cell0002': {},
                    'nova_spicehtml5proxy_external_cell0002': {}
                }
            }
        }
        self.assertDictEqual(expected, actual)
