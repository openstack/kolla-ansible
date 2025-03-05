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


import copy
from importlib.machinery import SourceFileLoader
import os
import sys
from unittest import mock

from docker import errors as docker_error
from docker.types import Ulimit
from oslotest import base

sys.modules['dbus'] = mock.MagicMock()

this_dir = os.path.dirname(sys.modules[__name__].__file__)
ansible_dir = os.path.join(this_dir, '..', '..', 'ansible')
kolla_container_file = os.path.join(ansible_dir,
                                    'library', 'kolla_container.py')
docker_worker_file = os.path.join(ansible_dir,
                                  'module_utils', 'kolla_docker_worker.py')
kc = SourceFileLoader('kolla_container', kolla_container_file).load_module()
dwm = SourceFileLoader('kolla_docker_worker', docker_worker_file).load_module()


FAKE_DATA = {

    'params': {
        'container_engine': 'docker',
        'api_version': None,
        'auth_username': None,
        'auth_password': None,
        'auth_registry': None,
        'restart_policy': None,
        'auth_email': None,
        'restart_retries': None,
        'graceful_timeout': None,
        'client_timeout': None,
        'command': None,
        'detach': True,
        'environment': None,
        'host_config': {
            'network_mode': 'host',
            'ipc_mode': '',
            'cap_add': None,
            'security_opt': None,
            'pid_mode': '',
            'privileged': False,
            'tmpfs': None,
            'volumes_from': None,
            'restart_policy': 'unless-stopped',
            'restart_retries': 10},
        'labels': {'build-date': '2016-06-02',
                   'kolla_version': '2.0.1',
                   'license': 'GPLv2',
                   'name': 'ubuntu Base Image',
                   'vendor': 'ubuntuOS'},
        'image': 'myregistrydomain.com:5000/ubuntu:16.04',
        'name': 'test_container',
        'remove_on_exit': True,
        'volumes': None,
        'tty': False,
    },

    'images': [
        {'Created': 1462317178,
         'Labels': {},
         'VirtualSize': 120759015,
         'ParentId': '',
         'RepoTags': ['myregistrydomain.com:5000/ubuntu:16.04'],
         'Id': 'sha256:c5f1cf30',
         'Size': 120759015},
        {'Created': 1461802380,
         'Labels': {},
         'VirtualSize': 403096303,
         'ParentId': '',
         'RepoTags': ['myregistrydomain.com:5000/centos:7.0'],
         'Id': 'sha256:336a6',
         'Size': 403096303}
    ],

    'containers': [
        {'Created': 1463578194,
         'Status': 'Up 23 hours',
         'HostConfig': {'NetworkMode': 'default'},
         'Id': 'e40d8e7187',
         'Image': 'myregistrydomain.com:5000/ubuntu:16.04',
         'ImageID': 'sha256:c5f1cf30',
         'Labels': {},
         'Names': '/my_container'},
        {'Created': 1463578195,
         'Status': 'Exited (0) 2 hours ago',
         'HostConfig': {'NetworkMode': 'default'},
         'Id': 'e40d8e7188',
         'Image': 'myregistrydomain.com:5000/ubuntu:16.04',
         'ImageID': 'sha256:c5f1cf30',
         'Labels': {},
         'Names': '/exited_container'},
    ],

    'container_inspect': {
        'Config': {
            'Env': ['KOLLA_BASE_DISTRO=ubuntu'],
            'Hostname': 'node2',
            'Volumes': {'/var/lib/kolla/config_files/': {}}},
        'Mounts': {},
        'NetworkSettings': {},
        'State': {}
    }

}

FAKE_DATA_COMMON_OPTS = {
    'auth_username': 'kevko',
    'auth_password': 'SECRET',
    'auth_registry': 'Quay.io/kolla',
    'restart_policy': 'unless-stopped',
    'auth_email': 'kevko@kevko.org',
    'restart_retries': 20,
    'environment': {
        'KOLLA_CONFIG_STRATEGY': 'COPY_ALWAYS'
    },
    'graceful_timeout': 60,
    'client_timeout': 150
}


def get_DockerWorker(mod_param, docker_api_version='1.40'):
    module = mock.MagicMock()
    module.params = copy.deepcopy(mod_param)

    common_options_defaults = {
        'auth_email': None,
        'auth_password': None,
        'auth_registry': None,
        'auth_username': None,
        'environment': None,
        'restart_policy': None,
        'restart_retries': 10,
        'api_version': 'auto',
        'graceful_timeout': 10,
        'client_timeout': 120,
        'container_engine': 'docker',
    }

    new_args = module.params.pop('common_options', dict()) or dict()
    env_module_environment = module.params.pop('environment', dict()) or dict()

    for k, v in module.params.items():
        if v is None:
            if k in common_options_defaults:
                if k in new_args:
                    # From ansible groups vars the common options
                    # can be string or int
                    if isinstance(new_args[k], str) and new_args[k].isdigit():
                        new_args[k] = int(new_args[k])
                    continue
                else:
                    if common_options_defaults[k] is not None:
                        new_args[k] = common_options_defaults[k]
            else:
                continue
        if v is not None:
            new_args[k] = v

    env_module_common_options = new_args.pop('environment', dict())
    new_args['environment'] = env_module_common_options
    new_args['environment'].update(env_module_environment)

    # if pid_mode = ""/None/False, remove it
    if not new_args.get('pid_mode', False):
        new_args.pop('pid_mode', None)
    # if ipc_mode = ""/None/False, remove it
    if not new_args.get('ipc_mode', False):
        new_args.pop('ipc_mode', None)

    module.params = new_args

    with mock.patch("docker.APIClient") as MockedDockerClientClass:
        MockedDockerClientClass.return_value._version = docker_api_version
        dw = dwm.DockerWorker(module)
        dw.systemd = mock.MagicMock()
        return dw


def inject_env_when_create_container(container_data):
    container_env = container_data.get('environment', dict()) or dict()
    container_svc_name = container_data.get('name').replace('_', '-')
    container_env.update({'KOLLA_SERVICE_NAME': container_svc_name})
    container_data['environment'] = container_env


class TestMainModule(base.BaseTestCase):

    def setUp(self):
        super(TestMainModule, self).setUp()
        self.fake_data = copy.deepcopy(FAKE_DATA)
        self.fake_data_common_opts = copy.deepcopy(FAKE_DATA)
        self.fake_data_common_opts['params']['common_options'] = \
            FAKE_DATA_COMMON_OPTS

    @mock.patch("kolla_container.traceback.format_exc")
    @mock.patch("kolla_docker_worker.get_docker_client")
    @mock.patch("kolla_container.generate_module")
    def test_docker_client_exception(self, mock_generate_module, mock_dclient,
                                     mock_traceback):
        module_mock = mock.MagicMock()
        mock_generate_module.return_value = module_mock
        mock_dclient.side_effect = AttributeError()
        mock_traceback.return_value = "Some very ugly traceback"
        kc.main()
        module_mock.fail_json.assert_called_once_with(
            changed=True, msg=repr("Some very ugly traceback"))

    @mock.patch("kolla_container.generate_module")
    def test_execute_module(self, mock_generate_module):
        module_mock = mock.MagicMock()
        module_mock.params = self.fake_data['params']
        module_mock.params["action"] = "check_image"
        mock_generate_module.return_value = module_mock
        with mock.patch(
            "ansible.module_utils.kolla_docker_worker.DockerWorker"
        ) as mock_dw:
            mock_dw.return_value.check_image.return_value = False
            mock_dw.return_value.changed = False
            mock_dw.return_value.result = {"some_key": "some_value"}
            kc.main()
            mock_dw.assert_called_once_with(module_mock)
            mock_dw.return_value.check_image.assert_called_once_with()
        module_mock.exit_json.assert_called_once_with(changed=False,
                                                      result=False,
                                                      some_key="some_value")

    def test_sets_dimensions_kernelmemory_supported_false(self):
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertTrue(self.dw._dimensions_kernel_memory_removed)

    def test_common_options_defaults(self):
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertEqual(self.dw.params['api_version'], 'auto')
        self.assertEqual(self.dw.params['restart_retries'], 10)
        self.assertEqual(self.dw.params['graceful_timeout'], 10)
        self.assertEqual(self.dw.params['client_timeout'], 120)
        self.assertEqual(self.dw.params['environment'], {})
        self.assertNotIn('auth_email', self.dw.params)
        self.assertNotIn('auth_password', self.dw.params)
        self.assertNotIn('auth_registry', self.dw.params)
        self.assertNotIn('auth_username', self.dw.params)
        self.assertNotIn('restart_policy', self.dw.params)

    def test_common_options(self):
        self.dw = get_DockerWorker(self.fake_data_common_opts['params'])
        self.assertEqual(self.dw.params['api_version'], 'auto')
        self.assertEqual(self.dw.params['restart_retries'], 20)
        self.assertEqual(self.dw.params['graceful_timeout'], 60)
        self.assertEqual(self.dw.params['client_timeout'], 150)
        self.assertEqual(self.dw.params['environment'],
                         {'KOLLA_CONFIG_STRATEGY': 'COPY_ALWAYS'})
        self.assertEqual(self.dw.params['auth_email'], 'kevko@kevko.org')
        self.assertEqual(self.dw.params['auth_password'], 'SECRET')
        self.assertEqual(self.dw.params['auth_registry'], 'Quay.io/kolla')
        self.assertEqual(self.dw.params['auth_username'], 'kevko')
        self.assertEqual(self.dw.params['restart_policy'], 'unless-stopped')

    def test_common_options_overriden(self):
        self.fake_data_common_opts['params']['restart_retries'] = 50
        self.fake_data_common_opts['params']['graceful_timeout'] = 100
        self.fake_data_common_opts['params']['auth_email'] = 'kevko@kevko.sk'
        self.dw = get_DockerWorker(self.fake_data_common_opts['params'])
        self.assertEqual(self.dw.params['api_version'], 'auto')
        self.assertEqual(self.dw.params['restart_retries'], 50)
        self.assertEqual(self.dw.params['graceful_timeout'], 100)
        self.assertEqual(self.dw.params['client_timeout'], 150)
        self.assertEqual(self.dw.params['environment'],
                         {'KOLLA_CONFIG_STRATEGY': 'COPY_ALWAYS'})
        self.assertEqual(self.dw.params['auth_email'], 'kevko@kevko.sk')
        self.assertEqual(self.dw.params['auth_password'], 'SECRET')
        self.assertEqual(self.dw.params['auth_registry'], 'Quay.io/kolla')
        self.assertEqual(self.dw.params['auth_username'], 'kevko')
        self.assertEqual(self.dw.params['restart_policy'], 'unless-stopped')


class TestContainer(base.BaseTestCase):

    def setUp(self):
        super(TestContainer, self).setUp()
        self.fake_data = copy.deepcopy(FAKE_DATA)

    def test_create_container_without_dimensions(self):
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.create_host_config = mock.MagicMock(
            return_value=self.fake_data['params']['host_config'])
        self.dw.create_container()
        self.assertTrue(self.dw.changed)

    def test_create_container_with_dimensions(self):
        self.fake_data['params']['dimensions'] = {'blkio_weight': 10}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.create_host_config = mock.MagicMock(
            return_value=self.fake_data['params']['host_config'])
        self.dw.create_container()
        inject_env_when_create_container(self.fake_data['params'])
        self.assertTrue(self.dw.changed)
        self.fake_data['params'].pop('dimensions')
        self.fake_data['params']['host_config']['blkio_weight'] = '10'
        expected_args = {'command', 'detach', 'environment',
                         'host_config', 'image', 'labels', 'name', 'tty',
                         'volumes'}
        self.dw.dc.create_container.assert_called_once_with(
            **{k: self.fake_data['params'][k] for k in expected_args})
        self.dw.dc.create_host_config.assert_called_with(
            cap_add=None, network_mode='host', ipc_mode=None,
            pid_mode=None, tmpfs=None, volumes_from=None, blkio_weight=10,
            security_opt=None, privileged=None)

    def test_create_container_wrong_dimensions(self):
        self.fake_data['params']['dimensions'] = {'random': 10}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.create_host_config = mock.MagicMock(
            return_value=self.fake_data['params']['host_config'])
        self.dw.create_container()
        self.dw.module.exit_json.assert_called_once_with(
            failed=True, msg=repr("Unsupported dimensions"),
            unsupported_dimensions=set(['random']))

    def test_create_container_with_healthcheck(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['CMD-SHELL', '/bin/check.sh']}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.create_host_config = mock.MagicMock(
            return_value=self.fake_data['params']['host_config'])
        self.dw.create_container()
        inject_env_when_create_container(self.fake_data['params'])
        self.assertTrue(self.dw.changed)
        expected_args = {'command', 'detach', 'environment', 'host_config',
                         'healthcheck', 'image', 'labels', 'name', 'tty',
                         'volumes'}
        self.dw.dc.create_container.assert_called_once_with(
            **{k: self.fake_data['params'][k] for k in expected_args})

    def test_create_container_with_None_healthcheck(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['NONE']}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.create_host_config = mock.MagicMock(
            return_value=self.fake_data['params']['host_config'])
        self.dw.create_container()
        inject_env_when_create_container(self.fake_data['params'])
        self.assertTrue(self.dw.changed)
        expected_args = {'command', 'detach', 'environment', 'host_config',
                         'image', 'labels', 'name', 'tty',
                         'volumes'}
        self.dw.dc.create_container.assert_called_once_with(
            **{k: self.fake_data['params'][k] for k in expected_args})

    def test_create_container_with_tmpfs(self):
        self.fake_data['params']['tmpfs'] = ['/tmp']  # nosec: B108
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.create_host_config = mock.MagicMock(
            return_value=self.fake_data['params']['host_config'])
        self.dw.create_container()
        self.assertTrue(self.dw.changed)
        self.assertEqual(['/tmp'],  # nosec: B108
                         self.dw.dc.create_host_config.call_args[1]['tmpfs'])

    def test_create_container_with_tmpfs_empty_string(self):
        self.fake_data['params']['tmpfs'] = ['']
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.create_host_config = mock.MagicMock(
            return_value=self.fake_data['params']['host_config'])
        self.dw.create_container()
        self.assertTrue(self.dw.changed)
        self.assertFalse(self.dw.dc.create_host_config.call_args[1]['tmpfs'])

    def test_create_container_create_volumes(self):
        self.fake_data['params']['volumes'] = [
            "kolla_logs:/var/log/kolla/",
            "fluentd_data:/var/lib/fluentd/data/",
            "/var/log/journal:/var/log/journal:ro",
            "/etc/kolla/fluentd/:/var/lib/kolla/config_files/:ro"
        ]
        self.dw = get_DockerWorker(self.fake_data['params'])

        self.dw.create_volume = mock.MagicMock()
        self.dw.create_container()
        expected_calls = [
            mock.call(name="kolla_logs"),
            mock.call(name="fluentd_data")
        ]

        self.dw.create_volume.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(self.dw.create_volume.call_count, 2)

    def test_start_container_without_pull(self):
        self.fake_data['params'].update({'auth_username': 'fake_user',
                                         'auth_password': 'fake_psw',
                                         'auth_registry': 'myrepo/myapp',
                                         'auth_email': 'fake_mail@foogle.com'})
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.dw.dc.containers = mock.MagicMock(params={'all': 'True'})
        new_container = copy.deepcopy(self.fake_data['containers'])
        new_container.append({'Names': '/test_container',
                              'Status': 'Up 2 seconds'})
        self.dw.dc.containers.side_effect = [self.fake_data['containers'],
                                             new_container]
        self.dw.check_container_differs = mock.MagicMock(return_value=False)
        self.dw.create_container = mock.MagicMock()
        self.dw.start_container()
        self.assertFalse(self.dw.changed)
        self.dw.create_container.assert_called_once_with()

    def test_start_container_with_duplicate_name(self):
        self.fake_data['params'].update({'name': 'my_container',
                                         'auth_username': 'fake_user',
                                         'auth_password': 'fake_psw',
                                         'auth_registry': 'myrepo/myapp',
                                         'auth_email': 'fake_mail@foogle.com'})
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.dw.dc.containers = mock.MagicMock(params={'all': 'True'})
        updated_cont_list = copy.deepcopy(self.fake_data['containers'])
        updated_cont_list.pop(0)
        self.dw.dc.containers.side_effect = [self.fake_data['containers'],
                                             self.fake_data['containers'],
                                             self.fake_data['containers'],
                                             updated_cont_list,
                                             self.fake_data['containers']
                                             ]
        self.dw.check_container_differs = mock.MagicMock(return_value=True)
        self.dw.dc.remove_container = mock.MagicMock()
        self.dw.create_container = mock.MagicMock()
        self.dw.start_container()
        self.assertTrue(self.dw.changed)
        self.dw.dc.remove_container.assert_called_once_with(
            container=self.fake_data['params'].get('name'),
            force=True)
        self.dw.create_container.assert_called_once_with()

    def test_start_container(self):
        self.fake_data['params'].update({'name': 'my_container',
                                         'auth_username': 'fake_user',
                                         'auth_password': 'fake_psw',
                                         'auth_registry': 'myrepo/myapp',
                                         'auth_email': 'fake_mail@foogle.com'})
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.fake_data['containers'][0].update(
            {'Status': 'Exited 2 days ago'})
        self.dw.dc.containers = mock.MagicMock(
            return_value=self.fake_data['containers'])
        self.dw.check_container_differs = mock.MagicMock(return_value=False)
        self.dw.start_container()
        self.assertTrue(self.dw.changed)
        self.dw.dc.start.assert_not_called()
        self.dw.systemd.start.assert_called_once()

    def test_start_container_no_detach(self):
        self.fake_data['params'].update({'name': 'my_container',
                                         'detach': False})
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.dw.dc.containers = mock.MagicMock(side_effect=[
            [], self.fake_data['containers'], self.fake_data['containers'],
            self.fake_data['containers']])
        self.dw.dc.wait = mock.MagicMock(return_value={'StatusCode': 0})
        self.dw.dc.logs = mock.MagicMock(
            side_effect=['fake stdout', 'fake stderr'])
        self.dw.start_container()
        self.assertTrue(self.dw.changed)
        name = self.fake_data['params'].get('name')
        self.dw.dc.wait.assert_called_once_with(name)
        self.dw.dc.logs.assert_has_calls([
            mock.call(name, stdout=True, stderr=False),
            mock.call(name, stdout=False, stderr=True)])
        self.dw.systemd.stop.assert_called_once_with()
        self.dw.dc.remove_container.assert_called_once_with(
            container=name, force=True)
        expected = {'rc': 0, 'stdout': 'fake stdout', 'stderr': 'fake stderr'}
        self.assertEqual(expected, self.dw.result)

    def test_start_container_no_systemd(self):
        self.fake_data['params'].update({'name': 'my_container',
                                         'restart_policy': 'oneshot',
                                         'auth_username': 'fake_user',
                                         'auth_password': 'fake_psw',
                                         'auth_registry': 'myrepo/myapp',
                                         'auth_email': 'fake_mail@foogle.com'})
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.fake_data['containers'][0].update(
            {'Status': 'Exited 2 days ago'})
        self.dw.dc.containers = mock.MagicMock(
            return_value=self.fake_data['containers'])
        self.dw.check_container_differs = mock.MagicMock(return_value=False)
        self.dw.dc.start = mock.MagicMock()
        self.dw.start_container()
        self.assertTrue(self.dw.changed)
        self.dw.dc.start.assert_called_once_with(
            container=self.fake_data['params']['name']
        )
        self.dw.systemd.start.assert_not_called()

    def test_start_container_systemd_start_fail(self):
        self.fake_data['params'].update({'name': 'my_container',
                                         'auth_username': 'fake_user',
                                         'auth_password': 'fake_psw',
                                         'auth_registry': 'myrepo/myapp',
                                         'auth_email': 'fake_mail@foogle.com'})
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.dc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.fake_data['containers'][0].update(
            {'Status': 'Exited 2 days ago'})
        self.dw.dc.containers = mock.MagicMock(
            return_value=self.fake_data['containers'])
        self.dw.check_container_differs = mock.MagicMock(return_value=False)
        self.dw.systemd.start = mock.Mock(return_value=False)
        self.dw.start_container()
        self.assertTrue(self.dw.changed)
        self.dw.dc.start.assert_not_called()
        self.dw.systemd.start.assert_called_once()
        self.dw.module.fail_json.assert_called_once_with(
            changed=True, msg='Container timed out',
            **self.fake_data['containers'][0])

    def test_stop_container(self):
        self.dw = get_DockerWorker({'name': 'my_container',
                                    'action': 'stop_container'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.dw.stop_container()

        self.assertTrue(self.dw.changed)
        self.dw.dc.containers.assert_called_once_with(all=True)
        self.dw.systemd.stop.assert_called_once()
        self.dw.dc.stop.assert_not_called()
        self.dw.module.fail_json.assert_not_called()

    def test_stop_container_no_systemd(self):
        self.dw = get_DockerWorker({'name': 'my_container',
                                    'action': 'stop_container',
                                    'restart_policy': 'oneshot'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.dw.systemd.check_unit_file.return_value = False
        self.dw.stop_container()

        self.assertTrue(self.dw.changed)
        self.dw.dc.containers.assert_called_once_with(all=True)
        self.dw.systemd.stop.assert_not_called()
        self.dw.dc.stop.assert_called_once_with(
            'my_container', timeout=10)
        self.dw.module.fail_json.assert_not_called()

    def test_stop_container_already_stopped(self):
        self.dw = get_DockerWorker({'name': 'exited_container',
                                    'action': 'stop_container'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.dw.stop_container()

        self.assertFalse(self.dw.changed)
        self.dw.dc.containers.assert_called_once_with(all=True)
        self.dw.module.fail_json.assert_not_called()
        self.dw.dc.stop.assert_not_called()

    def test_stop_container_not_exists(self):
        self.dw = get_DockerWorker({'name': 'fake_container',
                                    'action': 'stop_container'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.dw.stop_container()

        self.assertFalse(self.dw.changed)
        self.dw.dc.containers.assert_called_once_with(all=True)
        self.dw.dc.stop.assert_not_called()
        self.dw.module.fail_json.assert_called_once_with(
            msg="No such container: fake_container to stop")

    def test_stop_container_not_exists_ignore_missing(self):
        self.dw = get_DockerWorker({'name': 'fake_container',
                                    'action': 'stop_container',
                                    'ignore_missing': True})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.dw.stop_container()

        self.assertFalse(self.dw.changed)
        self.dw.dc.containers.assert_called_once_with(all=True)
        self.dw.dc.stop.assert_not_called()
        self.dw.module.fail_json.assert_not_called()

    def test_stop_and_remove_container(self):
        self.dw = get_DockerWorker({'name': 'my_container',
                                    'action': 'stop_and_remove_container'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.dw.stop_and_remove_container()

        self.assertTrue(self.dw.changed)
        self.dw.dc.containers.assert_called_with(all=True)
        self.dw.systemd.stop.assert_called_once()
        self.dw.dc.remove_container.assert_called_once_with(
            container='my_container', force=True)

    def test_stop_and_remove_container_not_exists(self):
        self.dw = get_DockerWorker({'name': 'fake_container',
                                    'action': 'stop_and_remove_container'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.dw.stop_and_remove_container()

        self.assertFalse(self.dw.changed)
        self.dw.dc.containers.assert_called_with(all=True)
        self.assertFalse(self.dw.systemd.stop.called)
        self.assertFalse(self.dw.dc.remove_container.called)

    def test_restart_container(self):
        self.dw = get_DockerWorker({'name': 'my_container',
                                    'action': 'restart_container'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.fake_data['container_inspect'].update(
            self.fake_data['containers'][0])
        self.dw.dc.inspect_container.return_value = (
            self.fake_data['container_inspect'])
        self.dw.restart_container()

        self.assertTrue(self.dw.changed)
        self.dw.dc.containers.assert_called_once_with(all=True)
        self.dw.systemd.restart.assert_called_once_with()

    def test_restart_container_no_systemd(self):
        self.dw = get_DockerWorker({'name': 'my_container',
                                    'action': 'stop_container',
                                    'restart_policy': 'oneshot'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.fake_data['container_inspect'].update(
            self.fake_data['containers'][0])
        self.dw.dc.inspect_container.return_value = (
            self.fake_data['container_inspect'])
        self.dw.restart_container()

        self.assertTrue(self.dw.changed)
        self.dw.dc.containers.assert_called_once_with(all=True)
        self.dw.dc.stop.assert_called_once_with(
            'my_container', timeout=10)
        self.dw.dc.start.assert_called_once_with('my_container')
        self.dw.module.fail_json.assert_not_called()

    def test_restart_container_not_exists(self):
        self.dw = get_DockerWorker({'name': 'fake-container',
                                    'action': 'restart_container'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.dw.restart_container()

        self.assertFalse(self.dw.changed)
        self.dw.dc.containers.assert_called_once_with(all=True)
        self.dw.module.fail_json.assert_called_once_with(
            msg="No such container: fake-container")

    def test_restart_container_systemd_timeout(self):
        self.dw = get_DockerWorker({'name': 'my_container',
                                    'action': 'restart_container'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.fake_data['container_inspect'].update(
            self.fake_data['containers'][0])
        self.dw.dc.inspect_container.return_value = (
            self.fake_data['container_inspect'])
        self.dw.systemd.restart = mock.Mock(return_value=False)
        self.dw.restart_container()

        self.assertTrue(self.dw.changed)
        self.dw.dc.containers.assert_called_with(all=True)
        self.dw.systemd.restart.assert_called_once_with()
        self.dw.module.fail_json.assert_called_once_with(
            changed=True, msg="Container timed out",
            **self.fake_data['containers'][0])

    def test_remove_container(self):
        self.dw = get_DockerWorker({'name': 'my_container',
                                    'action': 'remove_container'})
        self.dw.dc.containers.return_value = self.fake_data['containers']
        self.dw.remove_container()

        self.assertTrue(self.dw.changed)
        self.dw.dc.containers.assert_called_once_with(all=True)
        self.dw.dc.remove_container.assert_called_once_with(
            container='my_container',
            force=True
        )

    def test_recreate_or_restart_container_not_container(self):
        self.dw = get_DockerWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ALWAYS')})
        self.dw.check_container = mock.Mock(return_value=None)
        self.dw.start_container = mock.Mock()

        self.dw.recreate_or_restart_container()

        self.dw.start_container.assert_called_once_with()

    def test_recreate_or_restart_container_container_copy_always(self):
        self.dw = get_DockerWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ALWAYS')})
        self.dw.check_container = mock.Mock(
            return_value=self.fake_data['containers'][0])
        self.dw.restart_container = mock.Mock()
        self.dw.check_container_differs = mock.Mock(return_value=False)

        self.dw.recreate_or_restart_container()

        self.dw.restart_container.assert_called_once_with()

    def test_recreate_or_restart_container_container_copy_always_differs(self):
        self.dw = get_DockerWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ALWAYS')})
        self.dw.check_container = mock.Mock(
            return_value=self.fake_data['containers'][0])
        self.dw.check_image = mock.Mock(
            return_value=self.fake_data['images'][0])
        self.dw.start_container = mock.Mock()
        self.dw.remove_container = mock.Mock()
        self.dw.check_container_differs = mock.Mock(return_value=True)

        self.dw.recreate_or_restart_container()

        self.dw.check_image.assert_called_once_with()
        self.dw.remove_container.assert_called_once_with()
        self.dw.start_container.assert_called_once_with()

    def test_recreate_or_restart_container_container_copy_once(self):
        self.dw = get_DockerWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ONCE')})
        self.dw.check_container = mock.Mock(
            return_value=self.fake_data['containers'][0])
        self.dw.check_image = mock.Mock(
            return_value=self.fake_data['images'][0])
        self.dw.start_container = mock.Mock()
        self.dw.remove_container = mock.Mock()

        self.dw.recreate_or_restart_container()

        self.dw.check_image.assert_called_once_with()
        self.dw.remove_container.assert_called_once_with()
        self.dw.start_container.assert_called_once_with()

    def test_recreate_or_restart_container_pull_before_stop(self):
        # Testing fix for https://launchpad.net/bugs/1852572.
        self.dw = get_DockerWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ONCE')})
        self.dw.check_container = mock.Mock(
            return_value=self.fake_data['containers'][0])
        self.dw.check_image = mock.Mock(return_value=None)
        self.dw.pull_image = mock.Mock()
        self.dw.start_container = mock.Mock()
        self.dw.remove_container = mock.Mock()

        self.dw.recreate_or_restart_container()

        self.dw.check_image.assert_called_once_with()
        self.dw.pull_image.assert_called_once_with()
        self.dw.remove_container.assert_called_once_with()
        self.dw.start_container.assert_called_once_with()


class TestImage(base.BaseTestCase):

    def setUp(self):
        super(TestImage, self).setUp()
        self.fake_data = copy.deepcopy(FAKE_DATA)

    def test_check_image(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04'})
        self.dw.dc.images.return_value = self.fake_data['images']

        return_data = self.dw.check_image()
        self.assertFalse(self.dw.changed)
        self.dw.dc.images.assert_called_once_with()
        self.assertEqual(self.fake_data['images'][0], return_data)

    def test_check_image_before_docker_1_12(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/centos:7.0'})
        self.fake_data['images'][0]['RepoTags'] = []
        self.dw.dc.images.return_value = self.fake_data['images']

        return_data = self.dw.check_image()
        self.assertFalse(self.dw.changed)
        self.dw.dc.images.assert_called_once_with()
        self.assertEqual(self.fake_data['images'][1], return_data)

    def test_check_image_docker_1_12(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/centos:7.0'})
        self.fake_data['images'][0]['RepoTags'] = None
        self.dw.dc.images.return_value = self.fake_data['images']

        return_data = self.dw.check_image()
        self.assertFalse(self.dw.changed)
        self.dw.dc.images.assert_called_once_with()
        self.assertEqual(self.fake_data['images'][1], return_data)

    def test_compare_image(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04'})
        self.dw.dc.images.return_value = self.fake_data['images']
        container_info = {'Image': 'sha256:c5f1cf40',
                          'Config': {'myregistrydomain.com:5000/ubuntu:16.04'}
                          }

        return_data = self.dw.compare_image(container_info)
        self.assertFalse(self.dw.changed)
        self.dw.dc.images.assert_called_once_with()
        self.assertTrue(return_data)

    def test_compare_config_unchanged(self):
        self.dw = get_DockerWorker(FAKE_DATA['params'])
        job = mock.MagicMock()
        self.dw.dc.exec_create.return_value = job
        self.dw.dc.exec_start.return_value = 'fake output'
        self.dw.dc.exec_inspect.return_value = {'ExitCode': 0}
        return_data = self.dw.compare_config()
        self.dw.dc.exec_create.assert_called_once_with(
            FAKE_DATA['params']['name'],
            dwm.COMPARE_CONFIG_CMD,
            user='root')
        self.dw.dc.exec_start.assert_called_once_with(job)
        self.dw.dc.exec_inspect.assert_called_once_with(job)
        self.assertFalse(return_data)

    def test_compare_config_changed(self):
        self.dw = get_DockerWorker(FAKE_DATA['params'])
        job = mock.MagicMock()
        self.dw.dc.exec_create.return_value = job
        self.dw.dc.exec_start.return_value = 'fake output'
        self.dw.dc.exec_inspect.return_value = {'ExitCode': 1}
        return_data = self.dw.compare_config()
        self.dw.dc.exec_create.assert_called_once_with(
            FAKE_DATA['params']['name'],
            dwm.COMPARE_CONFIG_CMD,
            user='root')
        self.dw.dc.exec_start.assert_called_once_with(job)
        self.dw.dc.exec_inspect.assert_called_once_with(job)
        self.assertTrue(return_data)

    def test_compare_config_changed_container_exited(self):
        self.dw = get_DockerWorker(FAKE_DATA['params'])
        job = mock.MagicMock()
        self.dw.dc.exec_create.return_value = job
        self.dw.dc.exec_start.return_value = 'fake output'
        self.dw.dc.exec_inspect.return_value = {'ExitCode': 137}
        return_data = self.dw.compare_config()
        self.dw.dc.exec_create.assert_called_once_with(
            FAKE_DATA['params']['name'],
            dwm.COMPARE_CONFIG_CMD,
            user='root')
        self.dw.dc.exec_start.assert_called_once_with(job)
        self.dw.dc.exec_inspect.assert_called_once_with(job)
        self.assertTrue(return_data)

    def test_compare_config_changed_client_failure(self):
        self.dw = get_DockerWorker(FAKE_DATA['params'])
        job = mock.MagicMock()
        self.dw.dc.exec_create.return_value = job
        self.dw.dc.exec_start.return_value = 'fake output'
        failure_response = mock.MagicMock()
        failure_response.status_code = 409  # any client error should do here
        self.dw.dc.exec_inspect.side_effect = docker_error.APIError(
            message="foo",
            response=failure_response,
        )
        return_data = self.dw.compare_config()
        self.dw.dc.exec_create.assert_called_once_with(
            FAKE_DATA['params']['name'],
            dwm.COMPARE_CONFIG_CMD,
            user='root')
        self.dw.dc.exec_start.assert_called_once_with(job)
        self.dw.dc.exec_inspect.assert_called_once_with(job)
        self.assertTrue(return_data)

    def test_compare_config_error(self):
        self.dw = get_DockerWorker(FAKE_DATA['params'])
        job = mock.MagicMock()
        self.dw.dc.exec_create.return_value = job
        self.dw.dc.exec_start.return_value = 'fake output'
        self.dw.dc.exec_inspect.return_value = {'ExitCode': -1}
        self.assertRaises(Exception, self.dw.compare_config)  # noqa: H202
        self.dw.dc.exec_create.assert_called_once_with(
            FAKE_DATA['params']['name'],
            dwm.COMPARE_CONFIG_CMD,
            user='root')
        self.dw.dc.exec_start.assert_called_once_with(job)
        self.dw.dc.exec_inspect.assert_called_once_with(job)

    def test_compare_config_error_server_failure(self):
        self.dw = get_DockerWorker(FAKE_DATA['params'])
        job = mock.MagicMock()
        self.dw.dc.exec_create.return_value = job
        self.dw.dc.exec_start.return_value = 'fake output'
        failure_response = mock.MagicMock()
        failure_response.status_code = 500  # any server error should do here
        self.dw.dc.exec_inspect.side_effect = docker_error.APIError(
            message="foo",
            response=failure_response,
        )
        self.assertRaises(docker_error.APIError, self.dw.compare_config)
        self.dw.dc.exec_create.assert_called_once_with(
            FAKE_DATA['params']['name'],
            dwm.COMPARE_CONFIG_CMD,
            user='root')
        self.dw.dc.exec_start.assert_called_once_with(job)
        self.dw.dc.exec_inspect.assert_called_once_with(job)

    def test_get_image_id_not_exists(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04'})
        self.dw.dc.images.return_value = []

        return_data = self.dw.get_image_id()
        self.assertIsNone(return_data)

    def test_get_image_id_exists(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04'})
        self.dw.dc.images.return_value = ['sha256:47c3bdbcf99f0c1a36e4db']

        return_data = self.dw.get_image_id()
        self.assertEqual('sha256:47c3bdbcf99f0c1a36e4db', return_data)

    def test_pull_image_new(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04',
             'auth_username': 'fake_user',
             'auth_password': 'fake_psw',
             'auth_registry': 'myrepo/myapp',
             'auth_email': 'fake_mail@foogle.com'
             })
        self.dw.dc.pull.return_value = [
            b'{"status":"Pull complete","progressDetail":{},"id":"22f7"}\r\n',
            b'{"status":"Digest: sha256:47c3bdbcf99f0c1a36e4db"}\r\n',
            b'{"status":"Downloaded newer image for ubuntu:16.04"}\r\n'
        ]
        self.dw.dc.images.side_effect = [
            [],
            ['sha256:47c3bdbcf99f0c1a36e4db']
        ]

        self.dw.pull_image()
        self.dw.dc.pull.assert_called_once_with(
            repository='myregistrydomain.com:5000/ubuntu',
            tag='16.04',
            stream=True)
        self.assertTrue(self.dw.changed)

    def test_pull_image_exists(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04'})
        self.dw.dc.pull.return_value = [
            b'{"status":"Pull complete","progressDetail":{},"id":"22f7"}\r\n',
            b'{"status":"Digest: sha256:47c3bdbf0c1a36e4db"}\r\n',
            b'{"status":"mage is up to date for ubuntu:16.04"}\r\n'
        ]
        self.dw.dc.images.side_effect = [
            ['sha256:47c3bdbcf99f0c1a36e4db'],
            ['sha256:47c3bdbcf99f0c1a36e4db']
        ]

        self.dw.pull_image()
        self.dw.dc.pull.assert_called_once_with(
            repository='myregistrydomain.com:5000/ubuntu',
            tag='16.04',
            stream=True)
        self.assertFalse(self.dw.changed)

    def test_pull_image_not_exists(self):
        self.dw = get_DockerWorker(
            {'image': 'unknown:16.04'})
        self.dw.dc.pull.return_value = [
            b'{"error": "image unknown not found"}\r\n']

        self.dw.pull_image()
        self.dw.dc.pull.assert_called_once_with(
            repository='unknown',
            tag='16.04',
            stream=True)
        self.assertFalse(self.dw.changed)
        self.dw.module.fail_json.assert_called_once_with(
            msg="The requested image does not exist: unknown:16.04",
            failed=True)

    def test_pull_image_error(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04'})
        self.dw.dc.pull.return_value = [
            b'{"error": "unexpected error"}\r\n']

        self.dw.pull_image()
        self.dw.dc.pull.assert_called_once_with(
            repository='myregistrydomain.com:5000/ubuntu',
            tag='16.04',
            stream=True)
        self.assertFalse(self.dw.changed)
        self.dw.module.fail_json.assert_called_once_with(
            msg="Unknown error message: unexpected error",
            failed=True)

    def test_remove_image(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04',
             'action': 'remove_image'})
        self.dw.dc.images.return_value = self.fake_data['images']

        self.dw.remove_image()
        self.assertTrue(self.dw.changed)
        self.dw.dc.remove_image.assert_called_once_with(
            image='myregistrydomain.com:5000/ubuntu:16.04')

    def test_remove_image_not_exists(self):
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/non_existing:16.04',
             'action': 'remove_image'})
        self.dw.dc.images.return_value = self.fake_data['images']

        self.dw.remove_image()
        self.assertFalse(self.dw.changed)

    def test_remove_image_exception_409(self):
        resp = mock.MagicMock()
        resp.status_code = 409
        docker_except = docker_error.APIError('test error', resp)
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04',
             'action': 'remove_image'})
        self.dw.dc.images.return_value = self.fake_data['images']
        self.dw.dc.remove_image.side_effect = docker_except

        self.assertRaises(docker_error.APIError, self.dw.remove_image)
        self.assertTrue(self.dw.changed)
        self.dw.module.fail_json.assert_called_once_with(
            failed=True,
            msg=("Image 'myregistrydomain.com:5000/ubuntu:16.04' "
                 "is currently in-use")
        )

    def test_remove_image_exception_500(self):
        resp = mock.MagicMock()
        resp.status_code = 500
        docker_except = docker_error.APIError('test error', resp)
        self.dw = get_DockerWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04',
             'action': 'remove_image'})
        self.dw.dc.images.return_value = self.fake_data['images']
        self.dw.dc.remove_image.side_effect = docker_except

        self.assertRaises(docker_error.APIError, self.dw.remove_image)
        self.assertTrue(self.dw.changed)
        self.dw.module.fail_json.assert_called_once_with(
            failed=True,
            msg=("Server error")
        )


class TestVolume(base.BaseTestCase):

    def setUp(self):
        super(TestVolume, self).setUp()
        self.fake_data = copy.deepcopy(FAKE_DATA)
        self.volumes = {
            'Volumes':
            [{'Driver': 'local',
              'Labels': None,
              'Mountpoint': '/var/lib/docker/volumes/nova_compute/_data',
              'Name': 'nova_compute'},
             {'Driver': 'local',
              'Labels': None,
              'Mountpoint': '/var/lib/docker/volumes/mariadb/_data',
              'Name': 'mariadb'}]
        }

    def test_create_volume(self):
        self.dw = get_DockerWorker({'name': 'rabbitmq',
                                    'action': 'create_volume'})
        self.dw.dc.volumes.return_value = self.volumes

        self.dw.create_volume()
        self.dw.dc.volumes.assert_called_once_with()
        self.assertTrue(self.dw.changed)
        self.dw.dc.create_volume.assert_called_once_with(
            name='rabbitmq',
            driver='local',
            labels={'kolla_managed': 'true'})

    def test_create_volume_exists(self):
        self.dw = get_DockerWorker({'name': 'nova_compute',
                                    'action': 'create_volume'})
        self.dw.dc.volumes.return_value = self.volumes

        self.dw.create_volume()
        self.dw.dc.volumes.assert_called_once_with()
        self.assertFalse(self.dw.changed)

    def test_remove_volume(self):
        self.dw = get_DockerWorker({'name': 'nova_compute',
                                    'action': 'remove_volume'})
        self.dw.dc.volumes.return_value = self.volumes

        self.dw.remove_volume()
        self.assertTrue(self.dw.changed)
        self.dw.dc.remove_volume.assert_called_once_with(name='nova_compute')

    def test_remove_volume_not_exists(self):
        self.dw = get_DockerWorker({'name': 'rabbitmq',
                                    'action': 'remove_volume'})
        self.dw.dc.volumes.return_value = self.volumes

        self.dw.remove_volume()
        self.assertFalse(self.dw.changed)

    def test_remove_volume_exception(self):
        resp = mock.MagicMock()
        resp.status_code = 409
        docker_except = docker_error.APIError('test error', resp)
        self.dw = get_DockerWorker({'name': 'nova_compute',
                                    'action': 'remove_volume'})
        self.dw.dc.volumes.return_value = self.volumes
        self.dw.dc.remove_volume.side_effect = docker_except

        self.assertRaises(docker_error.APIError, self.dw.remove_volume)
        self.assertTrue(self.dw.changed)
        self.dw.module.fail_json.assert_called_once_with(
            failed=True,
            msg="Volume named 'nova_compute' is currently in-use"
        )


class TestAttrComp(base.BaseTestCase):

    def setUp(self):
        super(TestAttrComp, self).setUp()
        self.fake_data = copy.deepcopy(FAKE_DATA)

    def test_compare_cap_add_neg(self):
        container_info = {'HostConfig': dict(CapAdd=['data'])}
        self.dw = get_DockerWorker({'cap_add': ['data']})
        self.assertFalse(self.dw.compare_cap_add(container_info))

    def test_compare_cap_add_pos(self):
        container_info = {'HostConfig': dict(CapAdd=['data1'])}
        self.dw = get_DockerWorker({'cap_add': ['data2']})
        self.assertTrue(self.dw.compare_cap_add(container_info))

    def test_compare_ipc_mode_neg(self):
        container_info = {'HostConfig': dict(IpcMode='data')}
        self.dw = get_DockerWorker({'ipc_mode': 'data'})
        self.assertFalse(self.dw.compare_ipc_mode(container_info))

    def test_compare_ipc_mode_pos(self):
        container_info = {'HostConfig': dict(IpcMode='data1')}
        self.dw = get_DockerWorker({'ipc_mode': 'data2'})
        self.assertTrue(self.dw.compare_ipc_mode(container_info))

    def test_compare_security_opt_neg(self):
        container_info = {'HostConfig': dict(SecurityOpt=['data'])}
        self.dw = get_DockerWorker({'security_opt': ['data']})
        self.assertFalse(self.dw.compare_security_opt(container_info))

    def test_compare_security_opt_pos(self):
        container_info = {'HostConfig': dict(SecurityOpt=['data1'])}
        self.dw = get_DockerWorker({'security_opt': ['data2']})
        self.assertTrue(self.dw.compare_security_opt(container_info))

    def test_compare_pid_mode_neg(self):
        container_info = {'HostConfig': dict(PidMode='host')}
        self.dw = get_DockerWorker({'pid_mode': 'host'})
        self.assertFalse(self.dw.compare_pid_mode(container_info))

    def test_compare_pid_mode_pos(self):
        container_info = {'HostConfig': dict(PidMode='host1')}
        self.dw = get_DockerWorker({'pid_mode': 'host2'})
        self.assertTrue(self.dw.compare_pid_mode(container_info))

    def test_compare_cgroupns_mode_neg(self):
        container_info = {'HostConfig': dict(CgroupnsMode='host')}
        self.dw = get_DockerWorker({'cgroupns_mode': 'host'},
                                   docker_api_version='1.41')
        self.assertFalse(self.dw.compare_cgroupns_mode(container_info))

    def test_compare_cgroupns_mode_neg_backward_compat(self):
        container_info = {'HostConfig': dict(CgroupnsMode='')}
        self.dw = get_DockerWorker({'cgroupns_mode': 'host'},
                                   docker_api_version='1.41')
        self.assertFalse(self.dw.compare_cgroupns_mode(container_info))

    def test_compare_cgroupns_mode_ignore(self):
        container_info = {'HostConfig': dict(CgroupnsMode='private')}
        self.dw = get_DockerWorker({}, docker_api_version='1.41')
        self.assertFalse(self.dw.compare_cgroupns_mode(container_info))

    def test_compare_cgroupns_mode_pos(self):
        container_info = {'HostConfig': dict(CgroupnsMode='private')}
        self.dw = get_DockerWorker({'cgroupns_mode': 'host'},
                                   docker_api_version='1.41')
        self.assertTrue(self.dw.compare_cgroupns_mode(container_info))

    def test_compare_cgroupns_mode_pos_backward_compat(self):
        container_info = {'HostConfig': dict(CgroupnsMode='')}
        self.dw = get_DockerWorker({'cgroupns_mode': 'private'},
                                   docker_api_version='1.41')
        self.assertTrue(self.dw.compare_cgroupns_mode(container_info))

    def test_compare_cgroupns_mode_unsupported(self):
        container_info = {'HostConfig': dict()}
        self.dw = get_DockerWorker({'cgroupns_mode': 'host'})
        self.assertFalse(self.dw.compare_cgroupns_mode(container_info))

    def test_compare_privileged_neg(self):
        container_info = {'HostConfig': dict(Privileged=True)}
        self.dw = get_DockerWorker({'privileged': True})
        self.assertFalse(self.dw.compare_privileged(container_info))

    def test_compare_privileged_pos(self):
        container_info = {'HostConfig': dict(Privileged=True)}
        self.dw = get_DockerWorker({'privileged': False})
        self.assertTrue(self.dw.compare_privileged(container_info))

    def test_compare_labels_neg(self):
        container_info = {'Config': dict(Labels={'kolla_version': '2.0.1'})}
        self.dw = get_DockerWorker({'labels': {'kolla_version': '2.0.1'}})
        self.dw.check_image = mock.MagicMock(return_value=dict(
            Labels={'kolla_version': '2.0.1'}))
        self.assertFalse(self.dw.compare_labels(container_info))

    def test_compare_labels_pos(self):
        container_info = {'Config': dict(Labels={'kolla_version': '1.0.1'})}
        self.dw = get_DockerWorker({'labels': {'kolla_version': '2.0.1'}})
        self.dw.check_image = mock.MagicMock(return_value=dict(
            Labels={'kolla_version': '1.0.1'}))
        self.assertTrue(self.dw.compare_labels(container_info))

    def test_compare_tmpfs_neg(self):
        container_info = {'HostConfig': dict(Tmpfs=['foo'])}
        self.dw = get_DockerWorker({'tmpfs': ['foo']})

        self.assertFalse(self.dw.compare_tmpfs(container_info))

    def test_compare_tmpfs_neg_empty_string(self):
        container_info = {'HostConfig': dict()}
        self.dw = get_DockerWorker({'tmpfs': ['']})

        self.assertFalse(self.dw.compare_tmpfs(container_info))

    def test_compare_tmpfs_pos_different(self):
        container_info = {'HostConfig': dict(Tmpfs=['foo'])}
        self.dw = get_DockerWorker({'tmpfs': ['bar']})

        self.assertTrue(self.dw.compare_tmpfs(container_info))

    def test_compare_tmpfs_pos_empty_new(self):
        container_info = {'HostConfig': dict(Tmpfs=['foo'])}
        self.dw = get_DockerWorker({})

        self.assertTrue(self.dw.compare_tmpfs(container_info))

    def test_compare_tmpfs_pos_empty_current(self):
        container_info = {'HostConfig': dict()}
        self.dw = get_DockerWorker({'tmpfs': ['bar']})

        self.assertTrue(self.dw.compare_tmpfs(container_info))

    def test_compare_volumes_from_neg(self):
        container_info = {'HostConfig': dict(VolumesFrom=['777f7dc92da7'])}
        self.dw = get_DockerWorker({'volumes_from': ['777f7dc92da7']})

        self.assertFalse(self.dw.compare_volumes_from(container_info))

    def test_compare_volumes_from_post(self):
        container_info = {'HostConfig': dict(VolumesFrom=['777f7dc92da7'])}
        self.dw = get_DockerWorker({'volumes_from': ['ba8c0c54f0f2']})

        self.assertTrue(self.dw.compare_volumes_from(container_info))

    def test_compare_volumes_neg(self):
        container_info = {
            'Config': dict(Volumes=['/var/log/kolla/']),
            'HostConfig': dict(Binds=['kolla_logs:/var/log/kolla/:rw'])}
        self.dw = get_DockerWorker(
            {'volumes': ['kolla_logs:/var/log/kolla/:rw']})

        self.assertFalse(self.dw.compare_volumes(container_info))

    def test_compare_volumes_pos(self):
        container_info = {
            'Config': dict(Volumes=['/var/log/kolla/']),
            'HostConfig': dict(Binds=['kolla_logs:/var/log/kolla/:rw'])}
        self.dw = get_DockerWorker(
            {'volumes': ['/dev/:/dev/:rw']})

        self.assertTrue(self.dw.compare_volumes(container_info))

    def test_compare_environment_neg(self):
        container_info = {'Config': dict(
            Env=['KOLLA_CONFIG_STRATEGY=COPY_ALWAYS',
                 'KOLLA_BASE_DISTRO=ubuntu']
        )}
        self.dw = get_DockerWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ALWAYS',
                                KOLLA_BASE_DISTRO='ubuntu')})

        self.assertFalse(self.dw.compare_environment(container_info))

    def test_compare_environment_pos(self):
        container_info = {'Config': dict(
            Env=['KOLLA_CONFIG_STRATEGY=COPY_ALWAYS',
                 'KOLLA_BASE_DISTRO=ubuntu']
        )}
        self.dw = get_DockerWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ALWAYS',
                                KOLLA_BASE_DISTRO='centos')})

        self.assertTrue(self.dw.compare_environment(container_info))

    def test_compare_container_state_neg(self):
        container_info = {'State': dict(Status='running')}
        self.dw = get_DockerWorker({'state': 'running'})
        self.assertFalse(self.dw.compare_container_state(container_info))

    def test_compare_dimensions_pos(self):
        self.fake_data['params']['dimensions'] = {
            'blkio_weight': 10, 'mem_limit': 30}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        resp = self.dw.compare_dimensions(container_info)
        self.dw.module.fail_json.assert_not_called()
        self.assertTrue(resp)

    def test_compare_dimensions_using_short_notation_not_changed(self):
        self.fake_data['params']['dimensions'] = {
            'mem_limit': '1024', 'mem_reservation': '3M',
            'memswap_limit': '2g'}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 1024, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 2 * 1024 * 1024 * 1024,
            'MemoryReservation': 3 * 1024 * 1024, 'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        resp = self.dw.compare_dimensions(container_info)
        self.dw.module.fail_json.assert_not_called()
        self.assertFalse(resp)

    def test_compare_dimensions_invalid_unit(self):
        self.fake_data['params']['dimensions'] = {
            'mem_limit': '1024', 'mem_reservation': '3M',
            'memswap_limit': '2E'}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'Memory': 1024, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 2 * 1024 * 1024 * 1024,
            'MemoryReservation': 3 * 1024 * 1024, 'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.compare_dimensions(container_info)
        expected_msg = ("The docker dimension unit [e] is "
                        "not supported for the dimension [2E]."
                        " The currently supported units are "
                        "['b', 'k', 'm', 'g'].")
        self.dw.module.fail_json.assert_called_once_with(
            failed=True, msg=expected_msg)

    def test_compare_dimensions_using_short_notation_changed(self):
        self.fake_data['params']['dimensions'] = {
            'mem_limit': '10m', 'mem_reservation': '3M',
            'memswap_limit': '1g'}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 1024, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 2 * 1024 * 1024 * 1024,
            'MemoryReservation': 3 * 1024 * 1024, 'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        resp = self.dw.compare_dimensions(container_info)
        self.dw.module.fail_json.assert_not_called()
        self.assertTrue(resp)

    def test_compare_dimensions_neg(self):
        self.fake_data['params']['dimensions'] = {
            'blkio_weight': 10}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 10,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertFalse(self.dw.compare_dimensions(container_info))

    def test_compare_wrong_dimensions(self):
        self.fake_data['params']['dimensions'] = {
            'blki_weight': 0}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.compare_dimensions(container_info)
        self.dw.module.exit_json.assert_called_once_with(
            failed=True, msg=repr("Unsupported dimensions"),
            unsupported_dimensions=set(['blki_weight']))

    def test_compare_empty_dimensions(self):
        self.fake_data['params']['dimensions'] = dict()
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '1', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertTrue(self.dw.compare_dimensions(container_info))

    def test_compare_dimensions_removed_and_changed(self):
        self.fake_data['params']['dimensions'] = {
            'mem_reservation': 10}
        container_info = dict()
        # Here mem_limit and mem_reservation are already present
        # Now we are updating only 'mem_reservation'.
        # Ideally it should return True stating that the docker
        # dimensions have been changed.
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 10, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 10,
            'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertTrue(self.dw.compare_dimensions(container_info))

    def test_compare_dimensions_explicit_default(self):
        self.fake_data['params']['dimensions'] = {
            'mem_reservation': 0}
        container_info = dict()
        # Here mem_limit and mem_reservation are already present
        # Now we are updating only 'mem_reservation'.
        # Ideally it should return True stating that the docker
        # dimensions have been changed.
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertFalse(self.dw.compare_dimensions(container_info))

    def test_compare_dimensions_kernel_memory_unsupported(self):
        self.fake_data['params']['dimensions'] = {
            'kernel_memory': '1024'}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.compare_dimensions(container_info)
        self.dw.module.exit_json.assert_called_once_with(
            failed=True, msg=repr("Unsupported dimensions"),
            unsupported_dimensions=set(['kernel_memory']))

    def test_compare_container_state_pos(self):
        container_info = {'State': dict(Status='running')}
        self.dw = get_DockerWorker({'state': 'exited'})
        self.assertTrue(self.dw.compare_container_state(container_info))

    def test_compare_ulimits_pos(self):
        self.fake_data['params']['dimensions'] = {
            'ulimits': {'nofile': {'soft': 131072, 'hard': 131072}}}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertTrue(self.dw.compare_dimensions(container_info))

    def test_compare_ulimits_neg(self):
        self.fake_data['params']['dimensions'] = {
            'ulimits': {'nofile': {'soft': 131072, 'hard': 131072}}}
        ulimits_nofile = Ulimit(name='nofile',
                                soft=131072, hard=131072)
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': [ulimits_nofile]}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertFalse(self.dw.compare_dimensions(container_info))

    def test_compare_empty_new_healthcheck(self):
        container_info = dict()
        container_info['Config'] = {
            'Healthcheck': {
                'Test': [
                    "CMD-SHELL",
                    "/bin/check.sh"],
                "Interval": 30000000000,
                "Timeout": 30000000000,
                "StartPeriod": 5000000000,
                "Retries": 3}}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertTrue(self.dw.compare_healthcheck(container_info))

    def test_compare_empty_current_healthcheck(self):
        self.fake_data['params']['healthcheck'] = {
            'test': ['CMD-SHELL', '/bin/check.sh'],
            'interval': 30,
            'timeout': 30,
            'start_period': 5,
            'retries': 3}
        container_info = dict()
        container_info['Config'] = {}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertTrue(self.dw.compare_healthcheck(container_info))

    def test_compare_healthcheck_no_test(self):
        self.fake_data['params']['healthcheck'] = {
            'interval': 30,
            'timeout': 30,
            'start_period': 5,
            'retries': 3}
        container_info = dict()
        container_info['Config'] = {
            'Healthcheck': {
                'Test': [
                    "CMD-SHELL",
                    "/bin/check.sh"],
                "Interval": 30000000000,
                "Timeout": 30000000000,
                "StartPeriod": 5000000000,
                "Retries": 3}}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.compare_healthcheck(container_info)
        self.dw.module.exit_json.assert_called_once_with(
            failed=True, msg=repr("Missing healthcheck option"),
            missing_healthcheck=set(['test']))

    def test_compare_healthcheck_pos(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['CMD', '/bin/check']}
        container_info = dict()
        container_info['Config'] = {
            'Healthcheck': {
                'Test': [
                    "CMD-SHELL",
                    "/bin/check.sh"],
                "Interval": 30000000000,
                "Timeout": 30000000000,
                "StartPeriod": 5000000000,
                "Retries": 3}}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertTrue(self.dw.compare_healthcheck(container_info))

    def test_compare_healthcheck_neg(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['CMD-SHELL', '/bin/check.sh'],
             'interval': 30,
             'timeout': 30,
             'start_period': 5,
             'retries': 3}
        container_info = dict()
        container_info['Config'] = {
            "Healthcheck": {
                "Test": [
                    "CMD-SHELL",
                    "/bin/check.sh"],
                "Interval": 30000000000,
                "Timeout": 30000000000,
                "StartPeriod": 5000000000,
                "Retries": 3}}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertFalse(self.dw.compare_healthcheck(container_info))

    def test_compare_healthcheck_time_zero(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['CMD-SHELL', '/bin/check.sh'],
             'interval': 0,
             'timeout': 30,
             'start_period': 5,
             'retries': 3}
        container_info = dict()
        container_info['Config'] = {
            "Healthcheck": {
                "Test": [
                    "CMD-SHELL",
                    "/bin/check.sh"],
                "Interval": 30000000000,
                "Timeout": 30000000000,
                "StartPeriod": 5000000000,
                "Retries": 3}}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertTrue(self.dw.compare_healthcheck(container_info))

    def test_compare_healthcheck_time_wrong_type(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['CMD-SHELL', '/bin/check.sh'],
             'timeout': 30,
             'start_period': 5,
             'retries': 3}
        self.fake_data['params']['healthcheck']['interval'] = \
            {"broken": {"interval": "True"}}
        container_info = dict()
        container_info['Config'] = {
            "Healthcheck": {
                "Test": [
                    "CMD-SHELL",
                    "/bin/check.sh"],
                "Interval": 30000000000,
                "Timeout": 30000000000,
                "StartPeriod": 5000000000,
                "Retries": 3}}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertRaises(TypeError,
                          lambda: self.dw.compare_healthcheck(container_info))

    def test_compare_healthcheck_time_wrong_value(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['CMD-SHELL', '/bin/check.sh'],
             'timeout': 30,
             'start_period': 5,
             'retries': 3}
        self.fake_data['params']['healthcheck']['interval'] = "dog"
        container_info = dict()
        container_info['Config'] = {
            "Healthcheck": {
                "Test": [
                    "CMD-SHELL",
                    "/bin/check.sh"],
                "Interval": 30000000000,
                "Timeout": 30000000000,
                "StartPeriod": 5000000000,
                "Retries": 3}}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertRaises(ValueError,
                          lambda: self.dw.compare_healthcheck(container_info))

    def test_compare_healthcheck_opt_missing(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['CMD-SHELL', '/bin/check.sh'],
             'interval': 30,
             'timeout': 30,
             'retries': 3}
        container_info = dict()
        container_info['Config'] = {
            "Healthcheck": {
                "Test": [
                    "CMD-SHELL",
                    "/bin/check.sh"],
                "Interval": 30000000000,
                "Timeout": 30000000000,
                "StartPeriod": 5000000000,
                "Retries": 3}}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.compare_healthcheck(container_info)
        self.dw.module.exit_json.assert_called_once_with(
            failed=True, msg=repr("Missing healthcheck option"),
            missing_healthcheck=set(['start_period']))

    def test_compare_healthcheck_opt_extra(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['CMD-SHELL', '/bin/check.sh'],
             'interval': 30,
             'start_period': 5,
             'extra_option': 1,
             'timeout': 30,
             'retries': 3}
        container_info = dict()
        container_info['Config'] = {
            "Healthcheck": {
                "Test": [
                    "CMD-SHELL",
                    "/bin/check.sh"],
                "Interval": 30000000000,
                "Timeout": 30000000000,
                "StartPeriod": 5000000000,
                "Retries": 3}}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.dw.compare_healthcheck(container_info)
        self.dw.module.exit_json.assert_called_once_with(
            failed=True, msg=repr("Unsupported healthcheck options"),
            unsupported_healthcheck=set(['extra_option']))

    def test_compare_healthcheck_value_false(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['CMD-SHELL', '/bin/check.sh'],
             'interval': 30,
             'start_period': 5,
             'extra_option': 1,
             'timeout': 30,
             'retries': False}
        container_info = dict()
        container_info['Config'] = {
            "Healthcheck": {
                "Test": [
                    "CMD-SHELL",
                    "/bin/check.sh"],
                "Interval": 30000000000,
                "Timeout": 30000000000,
                "StartPeriod": 5000000000,
                "Retries": 3}}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertTrue(self.dw.compare_healthcheck(container_info))

    def test_parse_healthcheck_empty(self):
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertIsNone(self.dw.parse_healthcheck(
                          self.fake_data.get('params', {}).get('healthcheck')))

    def test_parse_healthcheck_test_none(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': 'NONE'}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertIsNone(self.dw.parse_healthcheck(
                          self.fake_data['params']['healthcheck']))

    def test_parse_healthcheck_test_none_brackets(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['NONE']}
        self.dw = get_DockerWorker(self.fake_data['params'])
        self.assertIsNone(self.dw.parse_healthcheck(
                          self.fake_data['params']['healthcheck']))
