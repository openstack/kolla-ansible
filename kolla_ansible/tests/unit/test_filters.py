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
from unittest import mock

import jinja2

from kolla_ansible import exception
from kolla_ansible import filters

from kolla_ansible.tests.unit.helpers import _to_bool


class TestFilters(unittest.TestCase):

    def setUp(self):
        # Bandit complains about Jinja2 autoescaping without nosec.
        self.env = jinja2.Environment()  # nosec
        self.env.filters['bool'] = _to_bool
        self.context = self._make_context()

    def _make_context(self, parent=None):
        if parent is None:
            parent = {}
        return self.env.context_class(
            self.env, parent=parent, name='dummy', blocks={})

    def test_service_enabled_true(self):
        service = {
            'enabled': True
        }
        self.assertTrue(filters.service_enabled(self.context, service))

    def test_service_enabled_yes(self):
        service = {
            'enabled': 'yes'
        }
        self.assertTrue(filters.service_enabled(self.context, service))

    def test_service_enabled_false(self):
        service = {
            'enabled': False
        }
        self.assertFalse(filters.service_enabled(self.context, service))

    def test_service_enabled_no(self):
        service = {
            'enabled': 'no'
        }
        self.assertFalse(filters.service_enabled(self.context, service))

    def test_service_enabled_no_attr(self):
        service = {}
        self.assertRaises(exception.FilterError,
                          filters.service_enabled, self.context, service)

    def test_service_mapped_to_host_host_in_groups_true(self):
        service = {
            'host_in_groups': True
        }
        self.assertTrue(filters.service_mapped_to_host(self.context, service))

    def test_service_mapped_to_host_host_in_groups_yes(self):
        service = {
            'host_in_groups': 'yes'
        }
        self.assertTrue(filters.service_mapped_to_host(self.context, service))

    def test_service_mapped_to_host_host_in_groups_false(self):
        service = {
            'host_in_groups': False
        }
        self.assertFalse(filters.service_mapped_to_host(self.context, service))

    def test_service_mapped_to_host_host_in_groups_no(self):
        service = {
            'host_in_groups': 'no'
        }
        self.assertFalse(filters.service_mapped_to_host(self.context, service))

    def test_service_mapped_to_host_in_group(self):
        service = {
            'group': 'foo'
        }
        context = self._make_context({'group_names': ['foo', 'bar']})
        self.assertTrue(filters.service_mapped_to_host(context, service))

    def test_service_mapped_to_host_not_in_group(self):
        service = {
            'group': 'foo'
        }
        context = self._make_context({'group_names': ['bar']})
        self.assertFalse(filters.service_mapped_to_host(context, service))

    def test_service_mapped_to_host_no_attr(self):
        service = {}
        self.assertRaises(exception.FilterError,
                          filters.service_mapped_to_host, self.context,
                          service)

    def test_extract_haproxy_services_empty_dict(self):
        example_service = {}
        actual = filters.extract_haproxy_services(
            self.context, example_service)
        # No change
        self.assertDictEqual({}, actual)

    def test_extract_haproxy_services_no_haproxy_dict(self):
        example_service = {
            "keystone-ssh": {
                "container_name": "keystone_ssh",
                "dimensions": {},
                "enabled": True,
                "group": "keystone",
                "healthcheck": {
                    "interval": "30",
                    "retries": "3",
                    "start_period": "5",
                    "test": [
                        "CMD-SHELL",
                        "healthcheck_listen sshd 8023"
                    ],
                    "timeout": "30"
                },
                "image": "keystone-ssh:latest",
                "volumes": [
                    "/etc/kolla/keystone-ssh/:/var/lib/kolla/config_files/:ro",
                    "/etc/localtime:/etc/localtime:ro",
                    "",
                    "kolla_logs:/var/log/kolla/",
                    "keystone_fernet_tokens:/etc/keystone/fernet-keys"
                ]
            }
        }
        actual = filters.extract_haproxy_services(self.context,
                                                  example_service)
        self.assertDictEqual({}, actual)

    def test_extract_haproxy_services_haproxy_dict(self):
        example_service = {
            "keystone": {
                "container_name": "keystone",
                "dimensions": {},
                "enabled": True,
                "group": "keystone",
                "haproxy": {
                    "keystone_admin": {
                        "enabled": True,
                        "external": False,
                        "listen_port": "35357",
                        "mode": "http",
                        "port": "35357",
                        "tls_backend": True
                    },
                    "keystone_external": {
                        "backend_http_extra": [],
                        "enabled": True,
                        "external": True,
                        "listen_port": "5000",
                        "mode": "http",
                        "port": "5000",
                        "tls_backend": True
                    },
                    "keystone_internal": {
                        "backend_http_extra": [],
                        "enabled": True,
                        "external": False,
                        "listen_port": "5000",
                        "mode": "http",
                        "port": "5000",
                        "tls_backend": True
                    }
                },
                "healthcheck": {
                    "interval": "30",
                    "retries": "3",
                    "start_period": "5",
                    "test": [
                        "CMD-SHELL",
                        "healthcheck_curl https://1.2.3.4:5000"
                    ],
                    "timeout": "30"
                },
                "image": "keystone:latest",
                "volumes": [
                    "/etc/kolla/keystone/:/var/lib/kolla/config_files/:ro",
                    "/etc/localtime:/etc/localtime:ro",
                    "",
                    "",
                    "kolla_logs:/var/log/kolla/",
                    "keystone_fernet_tokens:/etc/keystone/fernet-keys"
                ]
            }
        }
        expected = {
            'keystone_admin': {
                'enabled': True,
                'external': False,
                'listen_port': '35357',
                'mode': 'http',
                'port': '35357',
                'tls_backend': True
            },
            'keystone_external': {
                'backend_http_extra': [],
                'enabled': True,
                'external': True,
                'listen_port': '5000',
                'mode': 'http',
                'port': '5000',
                'tls_backend': True
            },
            'keystone_internal': {
                'backend_http_extra': [],
                'enabled': True,
                'external': False,
                'listen_port': '5000',
                'mode': 'http',
                'port': '5000',
                'tls_backend': True
            }
        }
        actual = filters.extract_haproxy_services(self.context,
                                                  example_service)
        self.assertDictEqual(expected, actual)

    def test_extract_two_services_with_haproxy_dict(self):
        example_service = {
            "glance-api": {
                "container_name": "glance_api",
                "dimensions": {},
                "enabled": True,
                "environment": {
                    "http_proxy": "",
                    "https_proxy": "",
                    "no_proxy": "127.0.0.1,localhost,1.2.3.4,1.2.3.4"
                },
                "group": "glance-api",
                "haproxy": {
                    "glance_api": {
                        "backend_http_extra": [
                            "timeout server 6h"
                        ],
                        "custom_member_list": [
                            "server someserver 1.2.3.4:9292 "
                            "check inter 2000 rise 2 fall 5",
                            ""
                        ],
                        "enabled": False,
                        "external": False,
                        "frontend_http_extra": [
                            "timeout client 6h"
                        ],
                        "mode": "http",
                        "port": "9292"
                    },
                    "glance_api_external": {
                        "backend_http_extra": [
                            "timeout server 6h"
                        ],
                        "custom_member_list": [
                            "server someserver 1.2.3.4:9292 "
                            "check inter 2000 rise 2 fall 5",
                            ""
                        ],
                        "enabled": False,
                        "external": True,
                        "frontend_http_extra": [
                            "timeout client 6h"
                        ],
                        "mode": "http",
                        "port": "9292"
                    }
                },
                "healthcheck": {
                    "interval": "30",
                    "retries": "3",
                    "start_period": "5",
                    "test": [
                        "CMD-SHELL",
                        "healthcheck_curl http://localhost:9292"
                    ],
                    "timeout": "30"
                },
                "host_in_groups": True,
                "image": "centos-source-glance-api:latest",
                "privileged": False,
                "volumes": [
                    "/etc/localtime:/etc/localtime:ro",
                    "",
                    "glance:/var/lib/glance/",
                    "",
                    "kolla_logs:/var/log/kolla/",
                    "",
                    ""
                ]
            },
            "glance-tls-proxy": {
                "container_name": "glance_tls_proxy",
                "dimensions": {},
                "enabled": True,
                "group": "glance-api",
                "haproxy": {
                    "glance_tls_proxy": {
                        "backend_http_extra": [
                            "timeout server 6h"
                        ],
                        "custom_member_list": [
                            "server someserver 1.2.3.4:9292 "
                            "check inter 2000 rise 2 fall 5 ssl verify "
                            "required ca-file ca-bundle.trust.crt",
                            ""
                        ],
                        "enabled": True,
                        "external": False,
                        "frontend_http_extra": [
                            "timeout client 6h"
                        ],
                        "mode": "http",
                        "port": "9292",
                        "tls_backend": "yes"
                    },
                    "glance_tls_proxy_external": {
                        "backend_http_extra": [
                            "timeout server 6h"
                        ],
                        "custom_member_list": [
                            "server someserver 1.2.3.4:9292 "
                            "check inter 2000 rise 2 fall 5 ssl verify "
                            "required ca-file ca-bundle.trust.crt",
                            ""
                        ],
                        "enabled": True,
                        "external": True,
                        "frontend_http_extra": [
                            "timeout client 6h"
                        ],
                        "mode": "http",
                        "port": "9292",
                        "tls_backend": "yes"
                    }
                },
                "healthcheck": {
                    "interval": "30",
                    "retries": "3",
                    "start_period": "5",
                    "test": [
                        "CMD-SHELL",
                        "healthcheck_curl -u openstack:asdf 1.2.3.4:9293"
                    ],
                    "timeout": "30"
                },
                "host_in_groups": True,
                "image": "centos-source-haproxy:latest",
                "volumes": [
                    "/etc/localtime:/etc/localtime:ro",
                    "",
                    "kolla_logs:/var/log/kolla/"
                ]
            }
        }
        expected = {
            "glance_api": {
                "backend_http_extra": [
                    "timeout server 6h"
                ],
                'custom_member_list': ['server someserver '
                                       '1.2.3.4:9292 check inter 2000 '
                                       'rise 2 fall 5',
                                       ''],
                "enabled": False,
                "external": False,
                "frontend_http_extra": [
                    "timeout client 6h"
                ],
                "mode": "http",
                "port": "9292"
            },
            "glance_api_external": {
                "backend_http_extra": [
                    "timeout server 6h"
                ],
                'custom_member_list': ['server someserver '
                                       '1.2.3.4:9292 check inter 2000 '
                                       'rise 2 fall 5',
                                       ''],
                "enabled": False,
                "external": True,
                "frontend_http_extra": [
                    "timeout client 6h"
                ],
                "mode": "http",
                "port": "9292"
            },
            "glance_tls_proxy": {
                "backend_http_extra": [
                    "timeout server 6h"
                ],
                'custom_member_list': ['server someserver 1.2.3.4:9292 '
                                       'check inter 2000 rise 2 fall 5 '
                                       'ssl verify required ca-file '
                                       'ca-bundle.trust.crt',
                                       ''],
                "enabled": True,
                "external": False,
                "frontend_http_extra": [
                    "timeout client 6h"
                ],
                "mode": "http",
                "port": "9292",
                "tls_backend": "yes"
            },
            "glance_tls_proxy_external": {
                "backend_http_extra": [
                    "timeout server 6h"
                ],
                'custom_member_list': ['server someserver 1.2.3.4:9292 '
                                       'check inter 2000 rise 2 fall 5 '
                                       'ssl verify required ca-file '
                                       'ca-bundle.trust.crt',
                                       ''],

                "enabled": True,
                "external": True,
                "frontend_http_extra": [
                    "timeout client 6h"
                ],
                "mode": "http",
                "port": "9292",
                "tls_backend": "yes"
            }
        }
        actual = filters.extract_haproxy_services(self.context,
                                                  example_service)
        self.assertDictEqual(expected, actual)

    def test_extract_haproxy_services_haproxy_dict_duplicate(self):
        example_service = {
            "keystone": {
                "container_name": "keystone",
                "dimensions": {},
                "enabled": True,
                "group": "keystone",
                "haproxy": {
                    "keystone_admin": {
                        "enabled": True,
                        "external": False,
                        "listen_port": "35357",
                        "mode": "http",
                        "port": "35357",
                        "tls_backend": True
                    },
                },
                "healthcheck": {
                    "interval": "30",
                    "retries": "3",
                    "start_period": "5",
                    "test": [
                        "CMD-SHELL",
                        "healthcheck_curl https://1.2.3.4:5000"
                    ],
                    "timeout": "30"
                },
                "image": "keystone:latest",
                "volumes": [
                    "/etc/kolla/keystone/:/var/lib/kolla/config_files/:ro",
                    "kolla_logs:/var/log/kolla/"
                ]
            },
            "keystone-ssh": {
                "container_name": "keystone_ssh",
                "dimensions": {},
                "enabled": True,
                "group": "keystone",
                "haproxy": {
                    "keystone_admin": {
                        "enabled": True,
                        "external": False,
                        "listen_port": "35357",
                        "mode": "http",
                        "port": "35357",
                        "tls_backend": True
                    },
                },
                "healthcheck": {
                    "interval": "30",
                    "retries": "3",
                    "start_period": "5",
                    "test": [
                        "CMD-SHELL",
                        "healthcheck_listen sshd 8023"
                    ],
                    "timeout": "30"
                },
                "image": "keystone-ssh:latest",
                "volumes": [
                    "/etc/kolla/keystone-ssh/:/var/lib/kolla/config_files/:ro",
                    "kolla_logs:/var/log/kolla/"
                ]
            }
        }
        self.assertRaises(exception.FilterError,
                          filters.extract_haproxy_services,
                          self.context, example_service)

    @mock.patch.object(filters, 'service_enabled')
    @mock.patch.object(filters, 'service_mapped_to_host')
    def test_service_enabled_and_mapped_to_host(self, mock_mapped,
                                                mock_enabled):
        service = {}
        mock_enabled.return_value = True
        mock_mapped.return_value = True
        self.assertTrue(filters.service_enabled_and_mapped_to_host(
            self.context, service))
        mock_enabled.assert_called_once_with(self.context, service)
        mock_mapped.assert_called_once_with(self.context, service)

    @mock.patch.object(filters, 'service_enabled')
    @mock.patch.object(filters, 'service_mapped_to_host')
    def test_service_enabled_and_mapped_to_host_disabled(self, mock_mapped,
                                                         mock_enabled):
        service = {}
        mock_enabled.return_value = False
        mock_mapped.return_value = True
        self.assertFalse(filters.service_enabled_and_mapped_to_host(
            self.context, service))
        mock_enabled.assert_called_once_with(self.context, service)
        self.assertFalse(mock_mapped.called)

    @mock.patch.object(filters, 'service_enabled')
    @mock.patch.object(filters, 'service_mapped_to_host')
    def test_service_enabled_and_mapped_to_host_not_mapped(self, mock_mapped,
                                                           mock_enabled):
        service = {}
        mock_enabled.return_value = True
        mock_mapped.return_value = False
        self.assertFalse(filters.service_enabled_and_mapped_to_host(
            self.context, service))
        mock_enabled.assert_called_once_with(self.context, service)
        mock_mapped.assert_called_once_with(self.context, service)

    @mock.patch.object(filters, 'service_enabled_and_mapped_to_host')
    def test_select_services_enabled_and_mapped_to_host(self, mock_seamth):
        services = {
            'foo': object(),
            'bar': object(),
            'baz': object(),
        }
        mock_seamth.side_effect = lambda _, s: s != services['bar']
        result = filters.select_services_enabled_and_mapped_to_host(
            self.context, services)
        expected = {
            'foo': services['foo'],
            'baz': services['baz'],
        }
        self.assertEqual(expected, result)
