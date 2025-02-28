# -*- coding: utf-8 -*-
#
# Copyright 2019 Radosław Piliszek (yoctozepto)
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

import unittest

import jinja2

from kolla_ansible.exception import FilterError
from kolla_ansible.kolla_address import kolla_address
from kolla_ansible.kolla_url import kolla_url
from kolla_ansible.put_address_in_context import put_address_in_context

from kolla_ansible.tests.unit.helpers import _to_bool


class TestAddressContextFilter(unittest.TestCase):

    def test_url_context(self):
        context = 'url'
        addr = '192.168.1.1'
        self.assertEqual(put_address_in_context(addr, context),
                         addr)
        addr = 'www.example.com'
        self.assertEqual(put_address_in_context(addr, context),
                         addr)
        addr = 'fd::'
        self.assertEqual(put_address_in_context(addr, context),
                         '[{}]'.format(addr))

    def test_memcache_context(self):
        context = 'memcache'
        addr = '192.168.1.1'
        self.assertEqual(put_address_in_context(addr, context),
                         addr)
        addr = 'www.example.com'
        self.assertEqual(put_address_in_context(addr, context),
                         addr)
        addr = 'fd::'
        self.assertEqual(put_address_in_context(addr, context),
                         'inet6:[{}]'.format(addr))

    def test_rabbitmq_context(self):
        context = 'rabbitmq'
        addr = '192.168.1.1'
        self.assertEqual(put_address_in_context(addr, context),
                         '192,168,1,1')
        addr = 'fd::'
        self.assertEqual(put_address_in_context(addr, context),
                         '16#fd,16#0,16#0,16#0,16#0,16#0,16#0,16#0')

    def test_unknown_context(self):
        self.assertRaises(FilterError, put_address_in_context, '', 'lol')


class TestKollaAddressFilter(unittest.TestCase):

    def setUp(self):
        # Bandit complains about Jinja2 autoescaping without nosec.
        self.env = jinja2.Environment()  # nosec
        self.env.filters['bool'] = _to_bool

    def _make_context(self, parent):
        return self.env.context_class(
            self.env, parent=parent, name='dummy', blocks={})

    def test_missing_config(self):
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                }
            }
        })
        self.assertRaises(FilterError, kolla_address, context, 'api')

    def test_valid_ipv4_config(self):
        addr = '192.0.2.1'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'api_address_family': 'ipv4',
                    'api_interface': 'fake-interface',
                    'ansible_facts': {
                        'fake_interface': {
                            'ipv4': {
                                'address': addr,
                            },
                        },
                    },
                },
            },
        })
        self.assertEqual(addr, kolla_address(context, 'api'))

    def test_valid_ipv6_config(self):
        addr = 'fd::'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'enable_haproxy': 'yes',
                    'api_address_family': 'ipv6',
                    'api_interface': 'fake-interface',
                    'ansible_facts': {
                        'fake_interface': {
                            'ipv6': [
                                {
                                    'address': addr,
                                    'scope': 'global',
                                    'prefix': 64,
                                },
                            ],
                        },
                    },
                },
            },
        })
        self.assertEqual(addr, kolla_address(context, 'api'))

    def test_missing_ipv6_config(self):
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'api_address_family': 'ipv6',
                    'api_interface': 'fake-interface',
                    'ansible_facts': {
                        'fake_interface': {
                        },
                    },
                },
            },
        })
        self.assertRaises(FilterError, kolla_address, context, 'api')

    def test_valid_ipv6_config_many_addr(self):
        addr = 'fd::'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'enable_haproxy': 'yes',
                    'api_address_family': 'ipv6',
                    'api_interface': 'fake-interface',
                    'ansible_facts': {
                        'fake_interface': {
                            'ipv6': [
                                {
                                    'address': addr,
                                    'scope': 'global',
                                    'prefix': 64,
                                },
                                {
                                    'address': addr + '1',
                                    'scope': 'link',
                                    'prefix': 64,
                                },
                                {
                                    'address': addr + '2',
                                    'scope': 'global',
                                    'prefix': 64,
                                },
                            ],
                        },
                    },
                },
            },
        })
        self.assertEqual(addr, kolla_address(context, 'api'))

    def test_invalid_ipv6_config_no_global(self):
        addr = 'fd::'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'api_address_family': 'ipv6',
                    'api_interface': 'fake-interface',
                    'ansible_facts': {
                        'fake_interface': {
                            'ipv6': [
                                {
                                    'address': addr,
                                    'scope': 'link',
                                    'prefix': 64,
                                },
                                {
                                    'address': addr + '1',
                                    'scope': 'link',
                                    'prefix': 64,
                                },
                            ],
                        },
                    },
                },
            },
        })
        self.assertRaises(FilterError, kolla_address, context, 'api')

    def test_valid_ipv6_config_prefix_128(self):
        addr = 'fd::'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'enable_haproxy': 'yes',
                    'api_address_family': 'ipv6',
                    'api_interface': 'fake-interface',
                    'ansible_facts': {
                        'fake_interface': {
                            'ipv6': [
                                {
                                    'address': addr,
                                    'scope': 'global',
                                    'prefix': 128,
                                },
                            ],
                        },
                    },
                },
            },
        })
        self.assertEqual(addr, kolla_address(context, 'api'))

    def test_valid_ipv6_config_ignore_internal_vip_address(self):
        addr = 'fd::'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'enable_haproxy': 'yes',
                    'kolla_internal_vip_address': addr + '1',
                    'api_address_family': 'ipv6',
                    'api_interface': 'fake-interface',
                    'ansible_facts': {
                        'fake_interface': {
                            'ipv6': [
                                {
                                    'address': addr + '1',
                                    'scope': 'global',
                                    'prefix': 128,
                                },
                                {
                                    'address': addr,
                                    'scope': 'global',
                                    'prefix': 128,
                                },
                            ],
                        },
                    },
                },
            },
        })
        self.assertEqual(addr, kolla_address(context, 'api'))

    def test_valid_ipv6_config_ignore_external_vip_address(self):
        addr = 'fd::'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'enable_haproxy': 'yes',
                    'kolla_external_vip_address': addr + '1',
                    'api_address_family': 'ipv6',
                    'api_interface': 'fake-interface',
                    'ansible_facts': {
                        'fake_interface': {
                            'ipv6': [
                                {
                                    'address': addr + '1',
                                    'scope': 'global',
                                    'prefix': 128,
                                },
                                {
                                    'address': addr,
                                    'scope': 'global',
                                    'prefix': 128,
                                },
                            ],
                        },
                    },
                },
            },
        })
        self.assertEqual(addr, kolla_address(context, 'api'))

    def test_valid_ipv6_config_do_not_ignore_any_vip_address(self):
        addr = 'fd::'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'enable_haproxy': 'no',
                    'kolla_external_vip_address': addr,
                    'kolla_internal_vip_address': addr,
                    'api_address_family': 'ipv6',
                    'api_interface': 'fake-interface',
                    'ansible_facts': {
                        'fake_interface': {
                            'ipv6': [
                                {
                                    'address': addr,
                                    'scope': 'global',
                                    'prefix': 128,
                                },
                            ],
                        },
                    },
                },
            },
        })
        self.assertEqual(addr, kolla_address(context, 'api'))

    def test_override_var_valid_ipv4(self):
        addr = '192.0.2.1'
        override_var = 'my_ip_address'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    override_var: addr,
                },
            },
        })
        self.assertEqual(
            addr, kolla_address(context, 'api', override_var=override_var))

    def test_override_var_valid_ipv6(self):
        addr = 'fd::'
        override_var = 'my_ip_address'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    override_var: addr,
                },
            },
        })
        self.assertEqual(
            addr, kolla_address(context, 'api', override_var=override_var))

    def test_override_var_invalid(self):
        addr = 'this-is-an-fqdn.example.com'
        override_var = 'my_ip_address'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    override_var: addr,
                },
            },
        })
        self.assertRaises(
            FilterError, kolla_address, context, 'api',
            override_var=override_var)

    def test_override_var_missing(self):
        addr = '192.0.2.1'
        override_var = 'my_ip_address'
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'api_address_family': 'ipv4',
                    'api_interface': 'fake-interface',
                    'ansible_facts': {
                        'fake_interface': {
                            'ipv4': {
                                'address': addr,
                            },
                        },
                    },
                },
            },
        })
        self.assertEqual(
            addr, kolla_address(context, 'api', None, override_var))


class TestKollaUrlFilter(unittest.TestCase):

    def test_https_443_path(self):
        protocol = 'https'
        fqdn = 'kolla.external'
        port = 443
        path = '/v2'
        self.assertEqual("https://kolla.external/v2",
                         kolla_url(fqdn, protocol, port, path))

    def test_http_80_path(self):
        protocol = 'http'
        fqdn = 'kolla.external'
        port = 80
        path = '/v2'
        self.assertEqual("http://kolla.external/v2",
                         kolla_url(fqdn, protocol, port, path))

    def test_https_8443_path(self):
        protocol = 'https'
        fqdn = 'kolla.external'
        port = 8443
        path = '/v2'
        self.assertEqual("https://kolla.external:8443/v2",
                         kolla_url(fqdn, protocol, port, path))

    def test_http_8080_path(self):
        protocol = 'http'
        fqdn = 'kolla.external'
        port = 8080
        path = '/v2'
        self.assertEqual("http://kolla.external:8080/v2",
                         kolla_url(fqdn, protocol, port, path))

    def test_https_443_nopath(self):
        protocol = 'https'
        fqdn = 'kolla.external'
        port = 443
        self.assertEqual("https://kolla.external",
                         kolla_url(fqdn, protocol, port))

    def test_http_80_nopath(self):
        protocol = 'http'
        fqdn = 'kolla.external'
        port = 80
        self.assertEqual("http://kolla.external",
                         kolla_url(fqdn, protocol, port))

    def test_https_8443_nopath(self):
        protocol = 'https'
        fqdn = 'kolla.external'
        port = 8443
        self.assertEqual("https://kolla.external:8443",
                         kolla_url(fqdn, protocol, port))

    def test_http_8080_nopath(self):
        protocol = 'http'
        fqdn = 'kolla.external'
        port = 8080
        self.assertEqual("http://kolla.external:8080",
                         kolla_url(fqdn, protocol, port))
