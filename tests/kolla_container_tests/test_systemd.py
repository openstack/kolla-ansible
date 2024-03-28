#!/usr/bin/env python

# Copyright 2016 NEC Corporation
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
import sys
from unittest import mock

from oslotest import base

sys.modules['dbus'] = mock.MagicMock()

this_dir = os.path.dirname(sys.modules[__name__].__file__)
ansible_dir = os.path.join(this_dir, '..', '..', 'ansible')
systemd_worker_file = os.path.join(ansible_dir,
                                   'module_utils', 'kolla_systemd_worker.py')
swm = SourceFileLoader('kolla_systemd_worker',
                       systemd_worker_file).load_module()


class TestSystemd(base.BaseTestCase):
    def setUp(self) -> None:
        super(TestSystemd, self).setUp()
        self.params_dict = dict(
            name='test',
            restart_policy='no',
            client_timeout=120,
            restart_retries=10,
            graceful_timeout=15
        )
        swm.sleep = mock.Mock()
        self.sw = swm.SystemdWorker(self.params_dict)

    def test_manager(self):
        self.assertIsNotNone(self.sw)
        self.assertIsNotNone(self.sw.manager)

    def test_start(self):
        self.sw.perform_action = mock.Mock(return_value=True)
        self.sw.wait_for_unit = mock.Mock(return_value=True)

        self.sw.start()
        self.sw.perform_action.assert_called_once_with(
            'StartUnit',
            'kolla-test-container.service',
            'replace'
        )

    def test_restart(self):
        self.sw.perform_action = mock.Mock(return_value=True)
        self.sw.wait_for_unit = mock.Mock(return_value=True)

        self.sw.restart()
        self.sw.perform_action.assert_called_once_with(
            'RestartUnit',
            'kolla-test-container.service',
            'replace'
        )

    def test_stop(self):
        self.sw.perform_action = mock.Mock(return_value=True)

        self.sw.stop()
        self.sw.perform_action.assert_called_once_with(
            'StopUnit',
            'kolla-test-container.service',
            'replace'
        )

    def test_reload(self):
        self.sw.perform_action = mock.Mock(return_value=True)

        self.sw.reload()
        self.sw.perform_action.assert_called_once_with(
            'Reload',
            'kolla-test-container.service',
            'replace'
        )

    def test_enable(self):
        self.sw.perform_action = mock.Mock(return_value=True)

        self.sw.enable()
        self.sw.perform_action.assert_called_once_with(
            'EnableUnitFiles',
            ['kolla-test-container.service'],
            False,
            True
        )

    def test_check_unit_change(self):
        self.sw.generate_unit_file = mock.Mock()
        self.sw.check_unit_file = mock.Mock(return_value=True)
        open_mock = mock.mock_open(read_data='test data')
        return_val = None

        with mock.patch('builtins.open', open_mock, create=True):
            return_val = self.sw.check_unit_change('test data')

        self.assertFalse(return_val)
        self.sw.generate_unit_file.assert_not_called()
        open_mock.assert_called_with(
            '/etc/systemd/system/kolla-test-container.service',
            'r'
        )
        open_mock.return_value.read.assert_called_once()

    def test_check_unit_change_diff(self):
        self.sw.generate_unit_file = mock.Mock()
        self.sw.check_unit_file = mock.Mock(return_value=True)
        open_mock = mock.mock_open(read_data='new data')
        return_val = None

        with mock.patch('builtins.open', open_mock, create=True):
            return_val = self.sw.check_unit_change('old data')

        self.assertTrue(return_val)
        self.sw.generate_unit_file.assert_not_called()
        open_mock.assert_called_with(
            '/etc/systemd/system/kolla-test-container.service',
            'r'
        )
        open_mock.return_value.read.assert_called_once()

    @mock.patch(
        'kolla_systemd_worker.TEMPLATE',
        """${name}, ${restart_policy},
        ${graceful_timeout}, ${restart_timeout},
        ${restart_retries}"""
    )
    def test_generate_unit_file(self):
        self.sw = swm.SystemdWorker(self.params_dict)
        p = self.params_dict
        ref_string = f"""{p.get('name')}, {p.get('restart_policy')},
        {p.get('graceful_timeout')}, {p.get('client_timeout')},
        {p.get('restart_retries')}"""

        ret_string = self.sw.generate_unit_file()

        self.assertEqual(ref_string, ret_string)

    def test_create_unit_file(self):
        self.sw.generate_unit_file = mock.Mock(return_value='test data')
        self.sw.check_unit_change = mock.Mock(return_value=True)
        self.sw.reload = mock.Mock()
        self.sw.enable = mock.Mock()
        open_mock = mock.mock_open()
        return_val = None

        with mock.patch('builtins.open', open_mock, create=True):
            return_val = self.sw.create_unit_file()

        self.assertTrue(return_val)
        open_mock.assert_called_with(
            '/etc/systemd/system/kolla-test-container.service',
            'w'
        )
        open_mock.return_value.write.assert_called_once_with('test data')
        self.sw.reload.assert_called_once()
        self.sw.enable.assert_called_once()

    def test_create_unit_file_no_change(self):
        self.sw.generate_unit_file = mock.Mock()
        self.sw.check_unit_change = mock.Mock(return_value=False)
        self.sw.reload = mock.Mock()
        self.sw.enable = mock.Mock()
        open_mock = mock.mock_open()

        return_val = self.sw.create_unit_file()

        self.assertFalse(return_val)
        open_mock.assert_not_called()
        self.sw.reload.assert_not_called()
        self.sw.enable.assert_not_called()

    def test_remove_unit_file(self):
        self.sw.check_unit_file = mock.Mock(return_value=True)
        os.remove = mock.Mock()
        self.sw.reload = mock.Mock()

        return_val = self.sw.remove_unit_file()

        self.assertTrue(return_val)
        os.remove.assert_called_once_with(
            '/etc/systemd/system/kolla-test-container.service'
        )
        self.sw.reload.assert_called_once()

    def test_get_unit_state(self):
        unit_list = [
            ('foo.service', '', 'loaded', 'active', 'exited'),
            ('kolla-test-container.service', '', 'loaded', 'active', 'running')
        ]
        self.sw.manager.ListUnits = mock.Mock(return_value=unit_list)

        state = self.sw.get_unit_state()

        self.sw.manager.ListUnits.assert_called_once()
        self.assertEqual('running', state)

    def test_get_unit_state_not_exist(self):
        unit_list = [
            ('foo.service', '', 'loaded', 'active', 'exited'),
            ('bar.service', '', 'loaded', 'active', 'running')
        ]
        self.sw.manager.ListUnits = mock.Mock(return_value=unit_list)

        state = self.sw.get_unit_state()

        self.sw.manager.ListUnits.assert_called_once()
        self.assertIsNone(state)

    def test_wait_for_unit(self):
        self.sw.get_unit_state = mock.Mock()
        self.sw.get_unit_state.side_effect = ['starting', 'running']

        result = self.sw.wait_for_unit(10)

        self.assertTrue(result)

    def test_wait_for_unit_timeout(self):
        self.sw.get_unit_state = mock.Mock()
        self.sw.get_unit_state.side_effect = [
            'starting', 'starting', 'failed', 'failed']

        result = self.sw.wait_for_unit(10)

        self.assertFalse(result)
