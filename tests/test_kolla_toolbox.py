# Copyright 2024 Tietoevry
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

import builtins
import contextlib
import json
import os
import sys

from ansible.module_utils import basic
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes
try:
    from ansible.module_utils.testing import patch_module_args
except ImportError:
    # TODO(dougszu): Remove this exception handler when Python 3.10 support
    # is not required. Python 3.10 isn't supported by Ansible Core 2.18 which
    # provides patch_module_args
    @contextlib.contextmanager
    def patch_module_args(args):
        serialized_args = to_bytes(json.dumps({'ANSIBLE_MODULE_ARGS': args}))
        with mock.patch.object(basic, '_ANSIBLE_ARGS', serialized_args):
            yield

from importlib.machinery import SourceFileLoader
from oslotest import base
from unittest import mock

# Import kolla_toolbox module using SourceFileLoader
this_dir = os.path.dirname(sys.modules[__name__].__file__)
ansible_dir = os.path.join(this_dir, '..', 'ansible')
kolla_toolbox_file = os.path.join(ansible_dir, 'library', 'kolla_toolbox.py')

kolla_toolbox = SourceFileLoader('kolla_toolbox',
                                 kolla_toolbox_file).load_module()


class AnsibleExitJson(BaseException):
    """Exception to be raised by module.exit_json and caught by a test case."""

    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.result = kwargs


class AnsibleFailJson(BaseException):
    """Exception to be raised by module.fail_json and caught by a test case."""

    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.result = kwargs


class MockAPIError(Exception):
    """Mock exception to be raised to simulate engine client APIError."""

    def __init__(self, message, explanation=None):
        super().__init__(message)
        self.explanation = explanation


class TestKollaToolboxModule(base.BaseTestCase):
    """Base class for the module's tests.

    Sets up methods that patch over the module's fail_json and exit_json,
    so that they dont just call sys.exit() and instead they return
    value of the result.
    """

    def setUp(self):
        super().setUp()

        self.fail_json_patch = mock.patch(
            'ansible.module_utils.basic.AnsibleModule.fail_json',
            side_effect=self.fail_json)
        self.exit_json_patch = mock.patch(
            'ansible.module_utils.basic.AnsibleModule.exit_json',
            side_effect=self.exit_json)

        self.fail_json_mock = self.fail_json_patch.start()
        self.exit_json_mock = self.exit_json_patch.start()

    def tearDown(self):
        super().tearDown()
        self.fail_json_patch.stop()
        self.exit_json_patch.stop()

    def exit_json(self, *args, **kwargs):
        raise AnsibleExitJson(kwargs)

    def fail_json(self, *args, **kwargs):
        raise AnsibleFailJson(kwargs)


class TestKollaToolboxMethods(TestKollaToolboxModule):
    """Class focused on testing the methods of KollaToolboxWorker."""

    def setUp(self):
        super().setUp()

        # Mock container client
        self.mock_container_client = mock.MagicMock()
        self.mock_container_errors = mock.MagicMock()
        self.mock_container_errors.APIError = MockAPIError

        # Mock Ansible module
        self.mock_ansible_module = mock.MagicMock()
        self.mock_ansible_module.fail_json.side_effect = self.fail_json
        self.mock_ansible_module.exit_json.side_effect = self.exit_json

        # Fake Kolla Toolbox Worker
        self.fake_ktbw = kolla_toolbox.KollaToolboxWorker(
            self.mock_ansible_module,
            self.mock_container_client,
            self.mock_container_errors)

    def test_ktb_container_missing_or_not_running(self):
        self.mock_container_client.containers.list.return_value = []

        error = self.assertRaises(AnsibleFailJson,
                                  self.fake_ktbw._get_toolbox_container)
        self.assertIn("kolla_toolbox container is missing or not running!",
                      error.result["msg"])

    def test_get_ktb_container_success(self):
        ktb_container = mock.MagicMock()
        other_container = mock.MagicMock()
        self.mock_container_client.containers.list.return_value = [
            ktb_container, other_container]

        ktb_container_returned = self.fake_ktbw._get_toolbox_container()

        self.assertEqual(ktb_container, ktb_container_returned)

    def test_format_module_args(self):
        module_args = [
            {
                'module_args': {},
                'expected_output': []
            },
            {
                'module_args': {
                    'path': '/some/folder',
                    'state': 'absent'},
                'expected_output': ["path='/some/folder'", "state='absent'"]
            }
        ]

        for args in module_args:
            formatted_args = self.fake_ktbw._format_module_args(
                args['module_args'])

            self.assertEqual(args['expected_output'], formatted_args)

    @mock.patch('kolla_toolbox.KollaToolboxWorker._format_module_args')
    def test_generate_correct_ktb_command(self, mock_formatter):
        fake_module_params = {
            'module_args': {
                'path': '/some/folder',
                'state': 'absent'
            },
            'module_extra_vars': {
                'variable': {
                    'key': 'pair',
                    'list': ['item1', 'item2']
                }
            },
            'user': 'root',
            'module_name': 'file'
        }

        mock_params = mock.MagicMock()
        mock_params.get.side_effect = lambda key: fake_module_params.get(key)
        self.mock_ansible_module.params = mock_params

        mock_formatter.side_effect = [
            ["path='/some/folder'", "state='absent'"],
            ['variable=\'{"key": "pair", "list": ["item1", "item2"]}\'']
        ]

        expected_command = ['ansible', 'localhost', '-m', 'file',
                            '-a', "path='/some/folder' state='absent'",
                            '-e', 'variable=\'{"key": "pair", '
                            '"list": ["item1", "item2"]}\'',
                            '--check']

        generated_command = self.fake_ktbw._generate_command()

        self.assertEqual(expected_command, generated_command)
        mock_formatter.assert_has_calls([
            mock.call(fake_module_params['module_args']),
            mock.call(fake_module_params['module_extra_vars'])
        ])

    def test_run_command_raises_apierror(self):
        ktb_container = mock.MagicMock()
        api_error = self.mock_container_errors.APIError(
            'API error occurred', explanation='Error explanation')
        ktb_container.exec_run.side_effect = api_error

        error = self.assertRaises(AnsibleFailJson,
                                  self.fake_ktbw._run_command,
                                  ktb_container,
                                  'some_command')
        self.assertIn('Container engine client encountered API error',
                      error.result['msg'])

    def test_run_command_success(self):
        exec_return_value = (0, b'data')
        ktb_container = mock.MagicMock()
        ktb_container.exec_run.return_value = exec_return_value
        self.mock_container_client.containers.list.return_value = [
            ktb_container]

        command_output = self.fake_ktbw._run_command(
            ktb_container, 'some_command')

        self.assertEqual(exec_return_value[1], command_output)
        self.assertIsInstance(command_output, bytes)
        ktb_container.exec_run.assert_called_once_with('some_command')

    def test_process_container_output_invalid_json(self):
        invalid_json = b'this is no json'

        error = self.assertRaises(AnsibleFailJson,
                                  self.fake_ktbw._process_container_output,
                                  invalid_json)
        self.assertIn('Parsing kolla_toolbox JSON output failed',
                      error.result['msg'])

    def test_process_container_output_invalid_structure(self):
        wrong_output_json = {
            'plays': [
                {
                    'tasks': [
                        {
                            'wrong': {
                                'control_node': {
                                    'pong': 'ping'
                                }
                            }
                        }
                    ]
                }
            ]
        }
        encoded_json = json.dumps(wrong_output_json).encode('utf-8')

        error = self.assertRaises(AnsibleFailJson,
                                  self.fake_ktbw._process_container_output,
                                  encoded_json)
        self.assertIn('Ansible JSON output has unexpected format',
                      error.result['msg'])

    def test_process_container_output_success(self):
        container_output_json = {
            'custom_stats': {},
            'global_custom_stats': {},
            'plays': [
                {
                    'tasks': [
                        {
                            'hosts': {
                                'localhost': {
                                    '_ansible_no_log': False,
                                    'action': 'ping',
                                    'changed': False,
                                    'invocation': {
                                        'module_args': {
                                            'data': 'pong'
                                        }
                                    },
                                    'ping': 'pong'
                                }
                            },
                        }
                    ]
                }
            ],
        }
        container_encoded_json = json.dumps(
            container_output_json).encode('utf-8')

        expected_output = {
            'action': 'ping',
            'changed': False,
            'invocation': {
                'module_args': {
                    'data': 'pong'
                }
            },
            'ping': 'pong'
        }
        generated_module_output = self.fake_ktbw._process_container_output(
            container_encoded_json)

        self.assertNotIn('_ansible_no_log', generated_module_output)
        self.assertEqual(expected_output, generated_module_output)


class TestModuleInteraction(TestKollaToolboxModule):
    """Class focused on testing user input data from playbook."""

    def test_create_ansible_module_missing_required_module_name(self):
        ansible_module_args = {
            'container_engine': 'docker'
        }
        with patch_module_args(ansible_module_args):
            error = self.assertRaises(AnsibleFailJson,
                                      kolla_toolbox.create_ansible_module)
        self.assertIn('missing required arguments: module_name',
                      error.result['msg'])

    def test_create_ansible_module_missing_required_container_engine(self):
        ansible_module_args = {
            'module_name': 'url'
        }
        with patch_module_args(ansible_module_args):
            error = self.assertRaises(AnsibleFailJson,
                                      kolla_toolbox.create_ansible_module)
        self.assertIn('missing required arguments: container_engine',
                      error.result['msg'])

    def test_create_ansible_module_invalid_container_engine(self):
        ansible_module_args = {
            'module_name': 'url',
            'container_engine': 'podmano'
        }
        with patch_module_args(ansible_module_args):
            error = self.assertRaises(AnsibleFailJson,
                                      kolla_toolbox.create_ansible_module)
        self.assertIn(
            'value of container_engine must be one of: podman, docker',
            error.result['msg']
        )

    def test_create_ansible_module_success(self):
        ansible_module_args = {
            'container_engine': 'docker',
            'module_name': 'file',
            'module_args': {
                'path': '/some/folder',
                'state': 'absent'
            },
            'module_extra_vars': {
                'variable': {
                    'key': 'pair',
                    'list': ['item1', 'item2']
                }
            },
            'user': 'root',
            'timeout': 180,
            'api_version': '1.5'
        }
        with patch_module_args(ansible_module_args):
            module = kolla_toolbox.create_ansible_module()
        self.assertIsInstance(module, AnsibleModule)
        self.assertEqual(ansible_module_args, module.params)


class TestContainerEngineClientIntraction(TestKollaToolboxModule):
    """Class focused on testing container engine client creation."""

    def setUp(self):
        super().setUp()
        self.module_to_mock_import = ''
        self.original_import = builtins.__import__

    def mock_import_error(self, name, globals, locals, fromlist, level):
        """Mock import function to raise ImportError for a specific module."""

        if name == self.module_to_mock_import:
            raise ImportError(f'No module named {name}')
        return self.original_import(name, globals, locals, fromlist, level)

    def test_podman_client_params(self):
        ansible_module_args = {
            'module_name': 'ping',
            'container_engine': 'podman',
            'api_version': '1.47',
            'timeout': 155
        }
        with patch_module_args(ansible_module_args):
            module = kolla_toolbox.create_ansible_module()
        mock_podman = mock.MagicMock()
        mock_podman_errors = mock.MagicMock()
        import_dict = {'podman': mock_podman,
                       'podman.errors': mock_podman_errors}

        with mock.patch.dict('sys.modules', import_dict):
            kolla_toolbox.create_container_client(module)
            mock_podman.PodmanClient.assert_called_with(
                base_url='http+unix:/run/podman/podman.sock',
                version='1.47',
                timeout=155
            )

    def test_docker_client_params(self):
        ansible_module_args = {
            'module_name': 'ping',
            'container_engine': 'docker',
            'api_version': '1.47',
            'timeout': 155
        }
        with patch_module_args(ansible_module_args):
            module = kolla_toolbox.create_ansible_module()
        mock_docker = mock.MagicMock()
        mock_docker_errors = mock.MagicMock()
        import_dict = {'docker': mock_docker,
                       'docker.errors': mock_docker_errors}

        with mock.patch.dict('sys.modules', import_dict):
            kolla_toolbox.create_container_client(module)
            mock_docker.DockerClient.assert_called_with(
                base_url='http+unix:/var/run/docker.sock',
                version='1.47',
                timeout=155
            )

    def test_create_container_client_podman_not_called_with_auto(self):
        ansible_module_args = {
            'module_name': 'ping',
            'container_engine': 'podman',
            'api_version': 'auto',
            'timeout': 90
        }
        with patch_module_args(ansible_module_args):
            module = kolla_toolbox.create_ansible_module()
        mock_podman = mock.MagicMock()
        mock_podman_errors = mock.MagicMock()
        import_dict = {'podman': mock_podman,
                       'podman.errors': mock_podman_errors}

        with mock.patch.dict('sys.modules', import_dict):
            kolla_toolbox.create_container_client(module)
            mock_podman.PodmanClient.assert_called_with(
                base_url='http+unix:/run/podman/podman.sock',
                timeout=90
            )

    def test_create_container_client_podman_importerror(self):
        ansible_module_args = {
            'module_name': 'ping',
            'container_engine': 'podman'
        }
        self.module_to_mock_import = 'podman'
        with patch_module_args(ansible_module_args):
            module = kolla_toolbox.create_ansible_module()

        with mock.patch('builtins.__import__',
                        side_effect=self.mock_import_error):
            error = self.assertRaises(AnsibleFailJson,
                                      kolla_toolbox.create_container_client,
                                      module)
            self.assertIn('The podman library could not be imported!',
                          error.result['msg'])

    def test_create_container_client_docker_importerror(self):
        ansible_module_args = {
            'module_name': 'ping',
            'container_engine': 'docker'
        }
        self.module_to_mock_import = 'docker'
        with patch_module_args(ansible_module_args):
            module = kolla_toolbox.create_ansible_module()

        with mock.patch('builtins.__import__',
                        side_effect=self.mock_import_error):
            error = self.assertRaises(AnsibleFailJson,
                                      kolla_toolbox.create_container_client,
                                      module)
            self.assertIn('The docker library could not be imported!',
                          error.result['msg'])
