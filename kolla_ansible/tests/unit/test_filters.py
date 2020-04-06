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


def _to_bool(value):
    """Simplified version of the bool filter.

    Avoids having a dependency on Ansible in unit tests.
    """
    if value == 'yes':
        return True
    if value == 'no':
        return False
    return bool(value)


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
