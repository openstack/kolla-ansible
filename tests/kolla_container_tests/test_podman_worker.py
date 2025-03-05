#!/usr/bin/env python

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
import unittest
from unittest import mock

from oslotest import base
from podman import errors as podman_error

sys.modules['dbus'] = mock.MagicMock()

this_dir = os.path.dirname(sys.modules[__name__].__file__)
ansible_dir = os.path.join(this_dir, '..', '..', 'ansible')
kolla_container_file = os.path.join(ansible_dir,
                                    'library', 'kolla_container.py')
podman_worker_file = os.path.join(ansible_dir,
                                  'module_utils', 'kolla_podman_worker.py')
kc = SourceFileLoader('kolla_container', kolla_container_file).load_module()
pwm = SourceFileLoader('kolla_podman_worker', podman_worker_file).load_module()

FAKE_DATA = {
    'params': {
        'container_engine': 'podman',
        'command': None,
        'detach': True,
        'environment': {},
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
        'client_timeout': 120,
    },

    'images': [
        {'Created': '2022-04-08T02:20:56.825403178Z',
         'Labels': {},
         'VirtualSize': 120759015,
         'Parent': '',
         'RepoTags': ['myregistrydomain.com:5000/ubuntu:16.04'],
         'Id': '7528a4009573fa8c5dbf4b6f5fad9f5b8d3a0fb90e22bb1b217211b553eb22cf',      # noqa: E501
         'Size': 120759015},
        {'Created': '2022-04-08T02:22:00.695203378Z',
         'Labels': {},
         'VirtualSize': 403096303,
         'Parent': '',
         'RepoTags': ['myregistrydomain.com:5000/centos:7.0'],
         'Id': '15529c81ae4a83084b076a16bc314e1af0b040a937f585311c87863fecc623a3',      # noqa: E501
         'Size': 403096303}
    ],

    'containers': [
        {'Created': '2022-06-23T14:30:35.595194629Z',
         'State': {'Status': 'running'},
         'HostConfig': {'NetworkMode': 'host'},
         'Id': '1663dfafec3bb59386e4a024416c8b0a872ae0984c9806322751d14b9f794c56',      # noqa: E501
         'ImageName': 'myregistrydomain.com:5000/ubuntu:16.04',
         'Image': '7528a4009573fa8c5dbf4b6f5fad9f5b8d3a0fb90e22bb1b217211b553eb22cf',   # noqa: E501
         'Labels': {},
         'Name': 'my_container'},
        {'Created': '2022-06-23T14:32:13.17545575Z',
         'State': {'Status': 'exited'},
         'HostConfig': {'NetworkMode': 'host'},
         'Id': '9404fc5f90118ddbbc31bb4c9462ad06aa7163eac1bc6d74c3e978143f10cc0c',      # noqa: E501
         'ImageName': 'myregistrydomain.com:5000/ubuntu:16.04',
         'Image': '15529c81ae4a83084b076a16bc314e1af0b040a937f585311c87863fecc623a3',   # noqa: E501
         'Labels': {},
         'Name': 'exited_container'},
    ],

    'container_inspect': {
        'Config': {
            'Env': ['KOLLA_BASE_DISTRO=ubuntu',
                    'KOLLA_INSTALL_TYPE=binary',
                    'KOLLA_INSTALL_METATYPE=rdo'],
            'Hostname': 'node2',
            'Volumes': {'/var/lib/kolla/config_files/': {}}},
        'Mounts': {},
        'NetworkSettings': {}
    }

}


class APIErrorStub(Exception):
    pass


def get_PodmanWorker(mod_param):
    module = mock.MagicMock()
    module.params = mod_param
    pw = pwm.PodmanWorker(module)
    pw.systemd = mock.MagicMock()
    pw.pc = mock.MagicMock()
    return pw


def construct_image(img_dict):
    image = mock.Mock()
    image.attrs = img_dict
    return image


def construct_volume(vol_dict):
    volume = mock.Mock()
    volume.attrs = vol_dict
    return volume


def construct_container(cont_dict):
    container = mock.Mock()
    container.name = cont_dict['Name']
    container.attrs = copy.deepcopy(cont_dict)
    container.status = cont_dict['State']['Status']
    return container


def get_containers(override=None):
    if override:
        cont_dicts = override
    else:
        cont_dicts = copy.deepcopy(FAKE_DATA['containers'])

    containers = []
    for c in cont_dicts:
        containers.append(construct_container(c))

    return containers


class TestMainModule(base.BaseTestCase):
    def setUp(self):
        super(TestMainModule, self).setUp()
        self.fake_data = copy.deepcopy(FAKE_DATA)

    @mock.patch("kolla_container.generate_module")
    def test_execute_module(self, mock_generate_module):
        module_mock = mock.MagicMock()
        module_mock.params = self.fake_data['params']
        module_mock.params["action"] = "check_image"
        mock_generate_module.return_value = module_mock
        with mock.patch(
            "ansible.module_utils.kolla_podman_worker.PodmanWorker"
        ) as mock_pw:
            mock_pw.return_value.check_image.return_value = False
            mock_pw.return_value.changed = False
            mock_pw.return_value.result = {"some_key": "some_value"}
            kc.main()
            mock_pw.assert_called_once_with(module_mock)
            mock_pw.return_value.check_image.assert_called_once_with()
        module_mock.exit_json.assert_called_once_with(changed=False,
                                                      result=False,
                                                      some_key="some_value")


class TestContainer(base.BaseTestCase):
    def setUp(self):
        super(TestContainer, self).setUp()
        self.fake_data = copy.deepcopy(FAKE_DATA)

    def test_create_container_fail(self):
        self.pw = get_PodmanWorker(self.fake_data['params'])
        container = mock.Mock()
        container.attrs = {}
        container.to_dict = mock.Mock(return_value={'some': 'value'})
        self.pw.pc.containers.create = mock.Mock(return_value=container)

        self.pw.create_container()
        self.assertFalse(self.pw.changed)
        self.pw.pc.containers.create.assert_called_once()
        self.pw.module.fail_json.assert_called_once_with(
            failed=True, msg='Creation failed', some='value')
        self.pw.systemd.create_unit_file.assert_not_called()

    def test_create_container_without_dimensions(self):
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.pw.prepare_container_args = mock.Mock(
            return_value={'some': 'value'})
        self.pw.systemd.create_unit_file = mock.Mock(return_value=True)

        self.pw.create_container()
        self.assertTrue(self.pw.changed)

    def test_create_container_with_dimensions(self):
        self.fake_data['params']['dimensions'] = {'blkio_weight': 10}
        self.pw = get_PodmanWorker(self.fake_data['params'].copy())
        self.pw.pc.containers.create = mock.MagicMock()

        self.pw.create_container()
        self.assertTrue(self.pw.changed)
        podman_create_kwargs = self.pw.pc.containers.create.call_args.kwargs.items()    # noqa
        self.pw.pc.containers.create.assert_called_once()
        self.assertIn(('blkio_weight', 10), podman_create_kwargs)

    def test_create_container_wrong_dimensions(self):
        self.fake_data['params']['dimensions'] = {'random': 10}
        self.pw = get_PodmanWorker(self.fake_data['params'])

        self.pw.create_container()
        self.pw.module.exit_json.assert_called_once_with(
            failed=True, msg=repr("Unsupported dimensions"),
            unsupported_dimensions=set(['random']))

    def test_create_container_with_healthcheck(self):
        hc = {'test': ['CMD-SHELL', '/bin/check.sh']}
        self.fake_data['params']['healthcheck'] = hc
        self.pw = get_PodmanWorker(self.fake_data['params'].copy())

        self.pw.create_container()
        self.assertTrue(self.pw.changed)
        podman_create_kwargs = self.pw.pc.containers.create.call_args.kwargs
        hc_call = podman_create_kwargs.get('healthcheck', None)
        self.pw.pc.containers.create.assert_called_once()
        self.assertIsNotNone(hc_call)
        self.assertEqual(hc, hc_call)

    def test_create_container_with_None_healthcheck(self):
        hc = {'test': ['NONE']}
        self.fake_data['params']['healthcheck'] = hc
        self.pw = get_PodmanWorker(self.fake_data['params'].copy())

        self.pw.create_container()
        self.assertTrue(self.pw.changed)
        podman_create_kwargs = self.pw.pc.containers.create.call_args.kwargs
        hc_call = podman_create_kwargs.get('healthcheck', None)
        self.pw.pc.containers.create.assert_called_once()
        self.assertIsNone(hc_call)

    @unittest.skip("Skipping because tmpfs is currently"
                   " not supported by podman API.")
    def test_create_container_with_tmpfs(self):
        self.fake_data['params']['tmpfs'] = ['/tmp']  # nosec: B108
        self.pw = get_PodmanWorker(self.fake_data['params'].copy())

        self.pw.create_container()
        self.assertTrue(self.pw.changed)
        self.assertEqual(['/tmp'],  # nosec: B108
                         self.pw.pc.containers.create.call_args[1]['tmpfs'])

    @unittest.skip("Skipping because tmpfs is currently"
                   " not supported by podman API.")
    def test_create_container_with_tmpfs_empty_string(self):
        self.fake_data['params']['tmpfs'] = ['']
        self.pw = get_PodmanWorker(self.fake_data['params'].copy())

        self.pw.create_container()
        self.assertTrue(self.pw.changed)
        self.assertFalse(self.pw.pc.containers.create.call_args[1]['tmpfs'])

    def test_create_container_create_volumes(self):
        self.fake_data['params']['volumes'] = [
            "kolla_logs:/var/log/kolla/",
            "fluentd_data:/var/lib/fluentd/data/",
            "/var/log/journal:/var/log/journal:ro",
            "/etc/kolla/fluentd/:/var/lib/kolla/config_files/:ro"
        ]
        self.pw = get_PodmanWorker(self.fake_data['params'])

        self.pw.create_volume = mock.MagicMock()
        self.pw.create_container()
        expected_calls = [
            mock.call(name="kolla_logs"),
            mock.call(name="fluentd_data")
        ]

        self.pw.create_volume.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(self.pw.create_volume.call_count, 2)

    def test_start_container_without_pull(self):
        self.fake_data['params'].update({'auth_username': 'fake_user',
                                         'auth_password': 'fake_psw',
                                         'auth_registry': 'myrepo/myapp',
                                         'auth_email': 'fake_mail@foogle.com'})
        self.pw = get_PodmanWorker(self.fake_data['params'].copy())
        self.pw.pc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.pw.pc.containers.list = mock.MagicMock(params={'all': 'True'})

        containers = get_containers()
        new_container = mock.Mock()
        new_container.name = 'test_container'
        new_container.status = 'running'
        self.pw.pc.containers.list.side_effect = [containers,
                                                  [*containers, new_container]]
        self.pw.check_container_differs = mock.MagicMock(return_value=False)
        self.pw.create_container = mock.MagicMock()

        self.pw.start_container()
        self.assertFalse(self.pw.changed)
        self.pw.create_container.assert_called_once_with()

    def test_start_container_with_duplicate_name(self):
        self.fake_data['params'].update({'name': 'my_container',
                                         'auth_username': 'fake_user',
                                         'auth_password': 'fake_psw',
                                         'auth_registry': 'myrepo/myapp',
                                         'auth_email': 'fake_mail@foogle.com'})
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.pw.pc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.pw.pc.containers.list = mock.MagicMock(params={'all': 'True'})
        full_cont_list = get_containers()
        updated_cont_list = full_cont_list[1:]
        self.pw.pc.containers.list.side_effect = [
            full_cont_list,
            full_cont_list,
            full_cont_list,
            updated_cont_list,
            full_cont_list
        ]
        self.pw.check_container_differs = mock.MagicMock(return_value=True)
        self.pw.create_container = mock.MagicMock()
        self.pw.start_container()
        self.assertTrue(self.pw.changed)
        full_cont_list[0].remove.assert_called_once_with(force=True)
        self.pw.create_container.assert_called_once_with()

    def test_start_container(self):
        self.fake_data['params'].update({'name': 'my_container',
                                         'auth_username': 'fake_user',
                                         'auth_password': 'fake_psw',
                                         'auth_registry': 'myrepo/myapp',
                                         'auth_email': 'fake_mail@foogle.com'})
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.pw.pc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.fake_data['containers'][0].update(
            {'State': {'Status': 'exited'}})
        self.pw.pc.containers.list = mock.MagicMock(
            return_value=get_containers(self.fake_data['containers']))
        self.pw.check_container_differs = mock.MagicMock(return_value=False)
        container = mock.Mock()
        self.pw.check_container = mock.Mock(return_value=container)

        self.pw.start_container()
        self.assertTrue(self.pw.changed)
        container.start.assert_not_called()
        self.pw.systemd.start.assert_called_once()

    def test_start_container_no_detach(self):
        self.fake_data['params'].update({'name': 'my_container',
                                         'detach': False})
        self.pw = get_PodmanWorker(self.fake_data['params'])
        full_cont_list = get_containers(self.fake_data['containers'])
        my_container = full_cont_list[0]

        self.pw.pc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.pw.pc.containers.list = mock.MagicMock(side_effect=[
            [],
            full_cont_list,
            full_cont_list,
            full_cont_list,
            full_cont_list
        ])
        my_container.remove = mock.Mock()
        my_container.wait = mock.MagicMock(return_value=0)
        my_container.logs = mock.MagicMock(side_effect=[
            ['fake stdout'.encode()],
            ['fake stderr'.encode()]])

        self.pw.start_container()
        self.assertTrue(self.pw.changed)
        my_container.wait.assert_called_once_with()
        my_container.logs.assert_has_calls([
            mock.call(stdout=True, stderr=False),
            mock.call(stdout=False, stderr=True)])
        self.pw.systemd.stop.assert_called_once_with()
        my_container.remove.assert_called_once_with(force=True)
        expected = {'rc': 0, 'stdout': 'fake stdout', 'stderr': 'fake stderr'}
        self.assertEqual(expected, self.pw.result)

    def test_start_container_no_systemd(self):
        self.fake_data['params'].update({'name': 'my_container',
                                         'restart_policy': 'oneshot',
                                         'auth_username': 'fake_user',
                                         'auth_password': 'fake_psw',
                                         'auth_registry': 'myrepo/myapp',
                                         'auth_email': 'fake_mail@foogle.com'})
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.pw.pc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.fake_data['containers'][0].update(
            {'State': {'Status': 'exited'}})
        self.pw.pc.containers.list = mock.MagicMock(
            return_value=get_containers(self.fake_data['containers']))
        self.pw.check_container_differs = mock.MagicMock(return_value=False)
        container = mock.Mock()
        self.pw.check_container = mock.Mock(return_value=container)

        self.pw.start_container()
        self.assertTrue(self.pw.changed)
        container.start.assert_called_once()
        self.pw.systemd.start.assert_not_called()

    def test_start_container_systemd_start_fail(self):
        self.fake_data['params'].update({'name': 'my_container',
                                         'auth_username': 'fake_user',
                                         'auth_password': 'fake_psw',
                                         'auth_registry': 'myrepo/myapp',
                                         'auth_email': 'fake_mail@foogle.com'})
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.pw.pc.images = mock.MagicMock(
            return_value=self.fake_data['images'])
        self.fake_data['containers'][0].update(
            {'State': {'Status': 'exited'}})
        self.pw.pc.containers.list = mock.MagicMock(
            return_value=get_containers(self.fake_data['containers']))
        self.pw.check_container_differs = mock.MagicMock(return_value=False)
        container = mock.Mock()
        container.attrs = {'some': 'value'}
        self.pw.check_container = mock.Mock(return_value=container)
        self.pw.systemd.start = mock.Mock(return_value=False)

        self.pw.start_container()
        self.assertTrue(self.pw.changed)
        container.start.assert_not_called()
        self.pw.systemd.start.assert_called_once()
        self.pw.module.fail_json.assert_called_once_with(
            changed=True, msg='Container timed out', some='value')

    def test_stop_container(self):
        self.pw = get_PodmanWorker({'name': 'my_container',
                                    'action': 'stop_container'})
        full_cont_list = get_containers(self.fake_data['containers'])
        container = full_cont_list[0]
        self.pw.pc.containers.list.return_value = full_cont_list
        self.pw.stop_container()

        self.assertTrue(self.pw.changed)
        self.pw.pc.containers.list.assert_called_once_with(all=True)
        self.pw.systemd.stop.assert_called_once()
        container.stop.assert_not_called()
        self.pw.module.fail_json.assert_not_called()

    def test_stop_container_no_systemd(self):
        self.pw = get_PodmanWorker({'name': 'my_container',
                                    'action': 'stop_container',
                                    'restart_policy': 'oneshot'})
        full_cont_list = get_containers(self.fake_data['containers'])
        container = full_cont_list[0]
        self.pw.pc.containers.list.return_value = full_cont_list
        self.pw.stop_container()

        self.assertTrue(self.pw.changed)
        self.pw.pc.containers.list.assert_called_once_with(all=True)
        self.pw.systemd.stop.assert_not_called()
        container.stop.assert_called_once()
        self.pw.module.fail_json.assert_not_called()

    def test_stop_container_already_stopped(self):
        self.pw = get_PodmanWorker({'name': 'exited_container',
                                    'action': 'stop_container'})
        full_cont_list = get_containers(self.fake_data['containers'])
        self.pw.pc.containers.list.return_value = full_cont_list
        exited_container = full_cont_list[1]
        self.pw.stop_container()

        self.assertFalse(self.pw.changed)
        self.pw.pc.containers.list.assert_called_once_with(all=True)
        self.pw.module.fail_json.assert_not_called()
        exited_container.stop.assert_not_called()

    def test_stop_container_not_exists(self):
        self.pw = get_PodmanWorker({'name': 'fake_container',
                                    'action': 'stop_container'})
        full_cont_list = get_containers(self.fake_data['containers'])
        self.pw.pc.containers.list.return_value = full_cont_list
        self.pw.stop_container()

        self.assertFalse(self.pw.changed)
        self.pw.pc.containers.list.assert_called_once_with(all=True)
        for cont in full_cont_list:
            cont.stop.assert_not_called()
        self.pw.systemd.stop.assert_not_called()
        self.pw.module.fail_json.assert_called_once_with(
            msg="No such container: fake_container to stop")

    def test_stop_container_not_exists_ignore_missing(self):
        self.pw = get_PodmanWorker({'name': 'fake_container',
                                    'action': 'stop_container',
                                    'ignore_missing': True})
        full_cont_list = get_containers(self.fake_data['containers'])
        self.pw.pc.containers.list.return_value = full_cont_list
        self.pw.stop_container()

        self.assertFalse(self.pw.changed)
        self.pw.pc.containers.list.assert_called_once_with(all=True)
        for cont in full_cont_list:
            cont.stop.assert_not_called()
        self.pw.systemd.stop.assert_not_called()
        self.pw.module.fail_json.assert_not_called()

    def test_stop_and_remove_container(self):
        self.pw = get_PodmanWorker({'name': 'my_container',
                                    'action': 'stop_and_remove_container'})
        full_cont_list = get_containers(self.fake_data['containers'])
        my_container = full_cont_list[0]
        self.pw.pc.containers.list.side_effect = [
            full_cont_list,
            full_cont_list,
            full_cont_list
        ]
        self.pw.stop_and_remove_container()

        self.assertTrue(self.pw.changed)
        self.pw.pc.containers.list.assert_called_with(all=True)
        self.pw.systemd.stop.assert_called_once()
        my_container.remove.assert_called_once_with(force=True)

    def test_stop_and_remove_container_not_exists(self):
        self.pw = get_PodmanWorker({'name': 'fake_container',
                                    'action': 'stop_and_remove_container'})
        full_cont_list = get_containers(self.fake_data['containers'])
        self.pw.pc.containers.list.return_value = full_cont_list
        self.pw.stop_and_remove_container()

        self.assertFalse(self.pw.changed)
        self.pw.pc.containers.list.assert_called_with(all=True)
        self.assertFalse(self.pw.systemd.stop.called)
        for cont in full_cont_list:
            self.assertFalse(cont.remove.called)

    def test_restart_container(self):
        self.pw = get_PodmanWorker({'name': 'my_container',
                                    'action': 'restart_container'})
        self.pw.pc.containers.list.return_value = get_containers(
            self.fake_data['containers'])
        self.pw.restart_container()

        self.assertTrue(self.pw.changed)
        self.pw.pc.containers.list.assert_called_once_with(all=True)
        self.pw.systemd.restart.assert_called_once_with()

    def test_restart_container_not_exists(self):
        self.pw = get_PodmanWorker({'name': 'fake-container',
                                    'action': 'restart_container'})
        self.pw.pc.containers.list.return_value = get_containers(
            self.fake_data['containers'])
        self.pw.restart_container()

        self.assertFalse(self.pw.changed)
        self.pw.pc.containers.list.assert_called_once_with(all=True)
        self.pw.module.fail_json.assert_called_once_with(
            msg="No such container: fake-container")

    def test_restart_systemd_timeout(self):
        self.pw = get_PodmanWorker({'name': 'my_container',
                                    'action': 'restart_container'})
        full_cont_list = get_containers(self.fake_data['containers'])
        my_container = full_cont_list[0]
        self.pw.pc.containers.list.return_value = full_cont_list
        self.pw.systemd.restart = mock.Mock(return_value=False)
        self.pw.restart_container()

        self.assertTrue(self.pw.changed)
        self.pw.pc.containers.list.assert_called_once_with(all=True)
        self.pw.systemd.restart.assert_called_once_with()
        self.pw.module.fail_json.assert_called_once_with(
            changed=True, msg="Container timed out", **my_container.attrs)

    def test_remove_container(self):
        self.pw = get_PodmanWorker({'name': 'my_container',
                                    'action': 'remove_container'})
        full_cont_list = get_containers(self.fake_data['containers'])
        self.pw.pc.containers.list.return_value = full_cont_list
        my_container = full_cont_list[0]
        self.pw.remove_container()

        self.assertTrue(self.pw.changed)
        self.pw.pc.containers.list.assert_called_once_with(all=True)
        my_container.remove.assert_called_once_with(force=True)

    def test_remove_container_api_error(self):
        self.pw = get_PodmanWorker({'name': 'my_container',
                                    'action': 'remove_container'})
        my_container = construct_container(self.fake_data['containers'][0])
        my_container.remove.side_effect = podman_error.APIError("dummy error")
        self.pw.check_container = mock.Mock(return_value=my_container)

        self.assertRaises(
            podman_error.APIError,
            self.pw.remove_container)
        self.assertTrue(self.pw.changed)
        my_container.remove.assert_called_once_with(force=True)

    def test_recreate_or_restart_container_not_container(self):
        self.pw = get_PodmanWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ALWAYS')})
        self.pw.check_container = mock.Mock(return_value=None)
        self.pw.start_container = mock.Mock()

        self.pw.recreate_or_restart_container()

        self.pw.start_container.assert_called_once_with()

    def test_recreate_or_restart_container_container_copy_always(self):
        self.pw = get_PodmanWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ALWAYS')})
        self.pw.check_container = mock.Mock(
            return_value=construct_container(self.fake_data['containers'][0]))
        self.pw.restart_container = mock.Mock()
        self.pw.check_container_differs = mock.Mock(return_value=False)

        self.pw.recreate_or_restart_container()

        self.pw.restart_container.assert_called_once_with()

    def test_recreate_or_restart_container_container_copy_always_differs(self):
        self.pw = get_PodmanWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ALWAYS')})
        self.pw.check_container = mock.Mock(
            return_value=construct_container(self.fake_data['containers'][0]))
        self.pw.ensure_image = mock.Mock()
        self.pw.start_container = mock.Mock()
        self.pw.remove_container = mock.Mock()
        self.pw.check_container_differs = mock.Mock(return_value=True)

        self.pw.recreate_or_restart_container()

        self.pw.ensure_image.assert_called_once_with()
        self.pw.remove_container.assert_called_once_with()
        self.pw.start_container.assert_called_once_with()

    def test_recreate_or_restart_container_container_copy_once(self):
        self.pw = get_PodmanWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ONCE')})
        self.pw.check_container = mock.Mock(
            return_value=construct_container(self.fake_data['containers'][0]))
        self.pw.ensure_image = mock.Mock()
        self.pw.start_container = mock.Mock()
        self.pw.remove_container = mock.Mock()

        self.pw.recreate_or_restart_container()

        self.pw.ensure_image.assert_called_once_with()
        self.pw.remove_container.assert_called_once_with()
        self.pw.start_container.assert_called_once_with()

    def test_recreate_or_restart_container_pull_before_stop(self):
        # Testing fix for https://launchpad.net/bugs/1852572.
        self.pw = get_PodmanWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ONCE')})
        self.pw.check_container = mock.Mock(
            return_value=construct_container(self.fake_data['containers'][0]))
        self.pw.check_image = mock.Mock(return_value=None)
        self.pw.pull_image = mock.Mock()
        self.pw.start_container = mock.Mock()
        self.pw.remove_container = mock.Mock()

        self.pw.recreate_or_restart_container()

        self.pw.check_image.assert_called_once_with()
        self.pw.pull_image.assert_called_once_with()
        self.pw.remove_container.assert_called_once_with()
        self.pw.start_container.assert_called_once_with()


class TestImage(base.BaseTestCase):
    def setUp(self):
        super(TestImage, self).setUp()
        self.fake_data = copy.deepcopy(FAKE_DATA)

    def test_check_image(self):
        self.pw = get_PodmanWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04'})
        self.pw.pc.images.get.return_value = construct_image(
            self.fake_data['images'][0])

        return_data = self.pw.check_image()
        self.assertFalse(self.pw.changed)
        self.pw.pc.images.get.assert_called_once_with(
            'myregistrydomain.com:5000/ubuntu:16.04')
        self.assertEqual(self.fake_data['images'][0], return_data)

    def test_compare_image(self):
        self.pw = get_PodmanWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04'})
        self.pw.pc.images.return_value = construct_image(
            self.fake_data['images'][0])
        container_info = {'Image': 'sha256:c5f1cf40',
                          'Config': {'myregistrydomain.com:5000/ubuntu:16.04'}
                          }

        return_data = self.pw.compare_image(container_info)
        self.assertFalse(self.pw.changed)
        self.pw.pc.images.get.assert_called_once_with(
            'myregistrydomain.com:5000/ubuntu:16.04')
        self.assertTrue(return_data)

    def test_compare_config_unchanged(self):
        self.fake_data['params']['name'] = 'my_container'
        self.pw = get_PodmanWorker(self.fake_data['params'])
        my_container = construct_container(self.fake_data['containers'][0])
        my_container.exec_run = mock.Mock(
            return_value=(0, 'fake_data'.encode()))
        self.pw.pc.containers.get.return_value = my_container

        return_data = self.pw.compare_config()
        self.pw.pc.containers.get.assert_called_once_with(
            self.fake_data['params']['name'])
        my_container.exec_run.assert_called_once_with(
            pwm.COMPARE_CONFIG_CMD,
            user='root')
        self.assertFalse(return_data)

    def test_compare_config_changed(self):
        self.fake_data['params']['name'] = 'my_container'
        self.pw = get_PodmanWorker(self.fake_data['params'])
        my_container = construct_container(self.fake_data['containers'][0])
        my_container.exec_run = mock.Mock(
            return_value=(1, 'fake_data'.encode()))
        self.pw.pc.containers.get.return_value = my_container

        return_data = self.pw.compare_config()
        self.pw.pc.containers.get.assert_called_once_with(
            self.fake_data['params']['name'])
        my_container.exec_run.assert_called_once_with(
            pwm.COMPARE_CONFIG_CMD,
            user='root')
        self.assertTrue(return_data)

    def test_compare_config_changed_container_exited(self):
        self.fake_data['params']['name'] = 'my_container'
        self.pw = get_PodmanWorker(self.fake_data['params'])
        my_container = construct_container(self.fake_data['containers'][0])
        my_container.status = 'exited'
        self.pw.pc.containers.get.return_value = my_container

        return_data = self.pw.compare_config()
        self.pw.pc.containers.get.assert_called_once_with(
            self.fake_data['params']['name'])
        my_container.exec_run.assert_not_called()
        self.assertTrue(return_data)

    @mock.patch('kolla_podman_worker.APIError',
                new_callable=lambda: APIErrorStub)
    def test_compare_config_changed_client_failure(self, stub_exception):
        stub_exception.is_client_error = mock.Mock(return_value=True)
        self.fake_data['params']['name'] = 'my_container'
        self.pw = get_PodmanWorker(self.fake_data['params'])
        my_container = construct_container(self.fake_data['containers'][0])
        my_container.exec_run = mock.Mock(side_effect=stub_exception())
        self.pw.pc.containers.get.return_value = my_container

        return_data = self.pw.compare_config()
        self.pw.pc.containers.get.assert_called_once_with(
            self.fake_data['params']['name'])
        my_container.exec_run.assert_called_once_with(
            pwm.COMPARE_CONFIG_CMD,
            user='root')
        self.assertTrue(return_data)

    def test_compare_config_error(self):
        self.fake_data['params']['name'] = 'my_container'
        self.pw = get_PodmanWorker(self.fake_data['params'])
        my_container = construct_container(self.fake_data['containers'][0])
        my_container.exec_run = mock.Mock(
            return_value=(-1, 'fake_data'.encode()))
        self.pw.pc.containers.get.return_value = my_container

        self.assertRaises(Exception, self.pw.compare_config)  # noqa: H202
        self.pw.pc.containers.get.assert_called_once_with(
            self.fake_data['params']['name'])
        my_container.exec_run.assert_called_once_with(
            pwm.COMPARE_CONFIG_CMD,
            user='root')

    def test_compare_config_error_server_failure(self):
        self.fake_data['params']['name'] = 'my_container'
        self.pw = get_PodmanWorker(self.fake_data['params'])
        my_container = construct_container(self.fake_data['containers'][0])
        my_container.exec_run = mock.Mock(
            side_effect=podman_error.APIError("foo"))
        self.pw.pc.containers.get.return_value = my_container

        self.assertRaises(podman_error.APIError, self.pw.compare_config)
        self.pw.pc.containers.get.assert_called_once_with(
            self.fake_data['params']['name'])
        my_container.exec_run.assert_called_once_with(
            pwm.COMPARE_CONFIG_CMD,
            user='root')

    def test_pull_image_new(self):
        self.pw = get_PodmanWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04',
             'auth_username': 'fake_user',
             'auth_password': 'fake_psw',
             'auth_registry': 'myrepo/myapp',
             'auth_email': 'fake_mail@foogle.com'
             })
        self.pw.pc.images.pull.return_value = construct_image(
            self.fake_data['images'][0])
        self.pw.pc.images.get.return_value = construct_image({})

        self.pw.pull_image()
        self.pw.pc.images.pull.assert_called_once_with(
            repository='myregistrydomain.com:5000/ubuntu',
            tag='16.04',
            tls_verify=False,
            stream=False,
            auth_config={'username': 'fake_user', 'password': 'fake_psw'}
        )
        self.assertTrue(self.pw.changed)

    def test_pull_image_exists(self):
        self.pw = get_PodmanWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04',
             'auth_username': 'fake_user',
             'auth_password': 'fake_psw',
             'auth_registry': 'myrepo/myapp',
             'auth_email': 'fake_mail@foogle.com'
             })
        image = construct_image(self.fake_data['images'][0])
        self.pw.pc.images.pull.return_value = image
        self.pw.pc.images.get.return_value = image

        self.pw.pull_image()
        self.pw.pc.images.pull.assert_called_once_with(
            repository='myregistrydomain.com:5000/ubuntu',
            tag='16.04',
            tls_verify=False,
            stream=False,
            auth_config={'username': 'fake_user', 'password': 'fake_psw'}
        )
        self.assertFalse(self.pw.changed)

    def test_pull_image_not_exists(self):
        self.pw = get_PodmanWorker(
            {'image': 'unknown:16.04'})
        self.pw.pc.images.pull.return_value = construct_image({})
        self.pw.check_image = mock.Mock(return_value={})

        self.pw.pull_image()
        self.pw.pc.images.pull.assert_called_once_with(
            repository='unknown',
            tag='16.04',
            tls_verify=False,
            stream=False,
        )
        self.assertFalse(self.pw.changed)
        self.pw.module.fail_json.assert_called_once_with(
            msg="The requested image does not exist: unknown:16.04",
            failed=True)

    def test_pull_image_error(self):
        self.pw = get_PodmanWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04'})
        self.pw.pc.images.pull = mock.Mock(
            side_effect=podman_error.APIError("unexpected error"))
        self.pw.pc.images.get.return_value = construct_image(
            self.fake_data['images'][0])

        self.pw.pull_image()
        self.pw.pc.images.pull.assert_called_once_with(
            repository='myregistrydomain.com:5000/ubuntu',
            tag='16.04',
            tls_verify=False,
            stream=False
        )
        self.assertFalse(self.pw.changed)
        self.pw.module.fail_json.assert_called_once_with(
            msg="Unknown error message: unexpected error",
            failed=True)

    def test_remove_image(self):
        self.pw = get_PodmanWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04',
             'action': 'remove_image'})
        image = construct_image(self.fake_data['images'][0])
        self.pw.pc.images.get.return_value = image

        self.pw.remove_image()
        self.assertTrue(self.pw.changed)
        image.remove.assert_called_once()

    def test_remove_image_not_exists(self):
        self.pw = get_PodmanWorker(
            {'image': 'myregistrydomain.com:5000/non_existing:16.04',
             'action': 'remove_image'})
        self.pw.pc.images.get.return_value = construct_image({})

        self.pw.remove_image()
        self.assertFalse(self.pw.changed)

    def test_remove_image_exception_409(self):
        resp = mock.MagicMock()
        resp.status_code = 409
        podman_except = podman_error.APIError('test error', resp)
        self.pw = get_PodmanWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04',
             'action': 'remove_image'})
        image = construct_image(self.fake_data['images'][0])
        image.remove = mock.Mock(side_effect=podman_except)
        self.pw.pc.images.get.return_value = image

        self.assertRaises(podman_error.APIError, self.pw.remove_image)
        self.assertTrue(self.pw.changed)
        self.pw.module.fail_json.assert_called_once_with(
            failed=True,
            msg=("Image 'myregistrydomain.com:5000/ubuntu:16.04' "
                 "is currently in-use")
        )

    def test_remove_image_server_error(self):
        resp = mock.MagicMock()
        resp.status_code = 500
        podman_except = podman_error.APIError('test error', resp)
        self.pw = get_PodmanWorker(
            {'image': 'myregistrydomain.com:5000/ubuntu:16.04',
             'action': 'remove_image'})
        image = construct_image(self.fake_data['images'][0])
        image.remove = mock.Mock(side_effect=podman_except)
        self.pw.pc.images.get.return_value = image

        self.assertRaises(podman_error.APIError, self.pw.remove_image)
        self.assertTrue(self.pw.changed)
        self.pw.module.fail_json.assert_called_once_with(
            failed=True,
            msg=(f"Internal error: {str(podman_except)}")
        )


class TestVolume(base.BaseTestCase):
    def setUp(self):
        super(TestVolume, self).setUp()
        self.fake_data = copy.deepcopy(FAKE_DATA)
        self.volumes = [
            {'Driver': 'local',
             'Labels': {},
             'Mountpoint': '/var/lib/docker/volumes/nova_compute/_data',
             'Name': 'nova_compute'},
            {'Driver': 'local',
             'Labels': {},
             'Mountpoint': '/var/lib/docker/volumes/mariadb/_data',
             'Name': 'mariadb'}]

    def test_parse_volumes_mounts(self):
        in_volumes = [
            '/etc/kolla/mariadb/:/var/lib/kolla/config_files/:shared',
            '/etc/localtime:/etc/localtime:ro',
            '',
        ]
        out_mounts = []
        out_volumes = {}
        expected_mounts = [
            {'source': '/etc/kolla/mariadb/',
             'target': '/var/lib/kolla/config_files/',
             'type': 'bind',
             'propagation': 'shared'},
            {'source': '/etc/localtime',
             'target': '/etc/localtime',
             'type': 'bind',
             'propagation': 'rprivate',
             'read_only': True}
        ]
        self.pw = get_PodmanWorker({})

        self.pw.parse_volumes(in_volumes, out_mounts, out_volumes)
        self.assertFalse(self.pw.changed)
        self.assertEqual(expected_mounts, out_mounts)
        self.assertEqual({}, out_volumes)
        self.pw.module.fail_json.assert_not_called()

    def test_parse_volumes_filtered_volumes(self):
        in_volumes = [
            '',
            'mariadb:/var/lib/mysql',
            'kolla_logs:/var/log/kolla/'
        ]
        out_mounts = []
        out_volumes = {}
        expected_volumes = {
            'mariadb': {'bind': '/var/lib/mysql', 'mode': 'rw'},
            'kolla_logs': {'bind': '/var/log/kolla/', 'mode': 'rw'}}
        self.pw = get_PodmanWorker({})

        self.pw.parse_volumes(in_volumes, out_mounts, out_volumes)
        self.assertFalse(self.pw.changed)
        self.assertEqual([], out_mounts)
        self.assertEqual(expected_volumes, out_volumes)
        self.pw.module.fail_json.assert_not_called()

    def test_create_volume(self):
        self.pw = get_PodmanWorker({'name': 'rabbitmq',
                                    'action': 'create_volume'})
        self.pw.pc.volumes.get.return_value = construct_volume({})

        self.pw.create_volume()
        self.pw.pc.volumes.get.assert_called_once_with('rabbitmq')
        self.assertTrue(self.pw.changed)
        self.pw.pc.volumes.create.assert_called_once_with(
            name='rabbitmq',
            driver='local',
            labels={'kolla_managed': 'true'})

    def test_create_volume_exists(self):
        self.pw = get_PodmanWorker({'name': 'nova_compute',
                                    'action': 'create_volume'})
        self.pw.pc.volumes.get.return_value = construct_volume(
            self.volumes[0])

        self.pw.create_volume()
        self.pw.pc.volumes.get.assert_called_once_with('nova_compute')
        self.assertFalse(self.pw.changed)

    def test_remove_volume(self):
        self.pw = get_PodmanWorker({'name': 'nova_compute',
                                    'action': 'remove_volume'})
        self.pw.pc.volumes.get.return_value = construct_volume(
            self.volumes[0])

        self.pw.remove_volume()
        self.assertTrue(self.pw.changed)
        self.pw.pc.volumes.remove.assert_called_once_with('nova_compute')

    def test_remove_volume_not_exists(self):
        self.pw = get_PodmanWorker({'name': 'rabbitmq',
                                    'action': 'remove_volume'})
        self.pw.pc.volumes.get.return_value = construct_volume({})

        self.pw.remove_volume()
        self.assertFalse(self.pw.changed)

    def test_remove_volume_exception(self):
        resp = mock.MagicMock()
        resp.status_code = 409
        docker_except = podman_error.APIError('test error', resp)
        self.pw = get_PodmanWorker({'name': 'nova_compute',
                                    'action': 'remove_volume'})
        self.pw.pc.volumes.get.return_value = construct_volume(self.volumes[0])
        self.pw.pc.volumes.remove.side_effect = docker_except

        self.assertRaises(podman_error.APIError, self.pw.remove_volume)
        self.assertTrue(self.pw.changed)
        self.pw.module.fail_json.assert_called_once_with(
            failed=True,
            msg="Volume named 'nova_compute' is currently in-use"
        )

    def test_remove_volume_error(self):
        resp = mock.MagicMock()
        resp.status_code = 500
        docker_except = podman_error.APIError(
            'test error', resp, 'server error')
        self.pw = get_PodmanWorker({'name': 'nova_compute',
                                    'action': 'remove_volume'})
        self.pw.pc.volumes.get.return_value = construct_volume(self.volumes[0])
        self.pw.pc.volumes.remove.side_effect = docker_except

        self.assertRaises(podman_error.APIError, self.pw.remove_volume)
        self.assertTrue(self.pw.changed)
        self.pw.module.fail_json.assert_called_once_with(
            failed=True,
            msg="Internal error: server error"
        )


class TestAttrComp(base.BaseTestCase):

    def setUp(self):
        super(TestAttrComp, self).setUp()
        self.fake_data = copy.deepcopy(FAKE_DATA)

    def test_compare_cap_add_neg(self):
        container_info = {'HostConfig': dict(CapAdd=['data'])}
        self.pw = get_PodmanWorker({'cap_add': ['data']})
        self.assertFalse(self.pw.compare_cap_add(container_info))

    def test_compare_cap_add_pos(self):
        container_info = {'HostConfig': dict(CapAdd=['data1'])}
        self.pw = get_PodmanWorker({'cap_add': ['data2']})
        self.assertTrue(self.pw.compare_cap_add(container_info))

    def test_compare_ipc_mode_neg(self):
        container_info = {'HostConfig': dict(IpcMode='data')}
        self.pw = get_PodmanWorker({'ipc_mode': 'data'})
        self.assertFalse(self.pw.compare_ipc_mode(container_info))

    def test_compare_ipc_mode_pos(self):
        container_info = {'HostConfig': dict(IpcMode='data1')}
        self.pw = get_PodmanWorker({'ipc_mode': 'data2'})
        self.assertTrue(self.pw.compare_ipc_mode(container_info))

    def test_compare_security_opt_neg(self):
        container_info = {'HostConfig': dict(SecurityOpt=['data'])}
        self.pw = get_PodmanWorker({'security_opt': ['data']})
        self.assertFalse(self.pw.compare_security_opt(container_info))

    def test_compare_security_opt_pos(self):
        container_info = {'HostConfig': dict(SecurityOpt=['data1'])}
        self.pw = get_PodmanWorker({'security_opt': ['data2']})
        self.assertTrue(self.pw.compare_security_opt(container_info))

    def test_compare_pid_mode_neg(self):
        container_info = {'HostConfig': dict(PidMode='host')}
        self.pw = get_PodmanWorker({'pid_mode': 'host'})
        self.assertFalse(self.pw.compare_pid_mode(container_info))

    def test_compare_pid_mode_pos(self):
        container_info = {'HostConfig': dict(PidMode='host1')}
        self.pw = get_PodmanWorker({'pid_mode': 'host2'})
        self.assertTrue(self.pw.compare_pid_mode(container_info))

    def test_compare_cgroupns_mode_neg(self):
        container_info = {'HostConfig': dict(CgroupMode='host')}
        self.pw = get_PodmanWorker({'cgroupns_mode': 'host'})
        self.assertFalse(self.pw.compare_cgroupns_mode(container_info))

    def test_compare_cgroupns_mode_neg_backward_compat(self):
        container_info = {'HostConfig': dict(CgroupMode='')}
        self.pw = get_PodmanWorker({'cgroupns_mode': 'host'})
        self.assertFalse(self.pw.compare_cgroupns_mode(container_info))

    def test_compare_cgroupns_mode_ignore(self):
        container_info = {'HostConfig': dict(CgroupMode='private')}
        self.pw = get_PodmanWorker({})
        self.assertFalse(self.pw.compare_cgroupns_mode(container_info))

    def test_compare_cgroupns_mode_pos(self):
        container_info = {'HostConfig': dict(CgroupMode='private')}
        self.pw = get_PodmanWorker({'cgroupns_mode': 'host', 'debug': True})
        self.assertTrue(self.pw.compare_cgroupns_mode(container_info))

    def test_compare_cgroupns_mode_pos_backward_compat(self):
        container_info = {'HostConfig': dict(CgroupMode='')}
        self.pw = get_PodmanWorker({'cgroupns_mode': 'private', 'debug': True})
        self.assertTrue(self.pw.compare_cgroupns_mode(container_info))

    def test_compare_cgroupns_mode_unsupported(self):
        container_info = {'HostConfig': dict()}
        self.pw = get_PodmanWorker({'cgroupns_mode': 'host'})
        self.assertFalse(self.pw.compare_cgroupns_mode(container_info))

    def test_compare_privileged_neg(self):
        container_info = {'HostConfig': dict(Privileged=True)}
        self.pw = get_PodmanWorker({'privileged': True})
        self.assertFalse(self.pw.compare_privileged(container_info))

    def test_compare_privileged_pos(self):
        container_info = {'HostConfig': dict(Privileged=True)}
        self.pw = get_PodmanWorker({'privileged': False})
        self.assertTrue(self.pw.compare_privileged(container_info))

    def test_compare_labels_neg(self):
        container_info = {'Config': dict(Labels={'kolla_version': '2.0.1'})}
        self.pw = get_PodmanWorker({'labels': {'kolla_version': '2.0.1'}})
        self.pw.check_image = mock.MagicMock(return_value=dict(
            Labels={'kolla_version': '2.0.1'}))
        self.assertFalse(self.pw.compare_labels(container_info))

    def test_compare_labels_pos(self):
        container_info = {'Config': dict(Labels={'kolla_version': '1.0.1'})}
        self.pw = get_PodmanWorker({'labels': {'kolla_version': '2.0.1'}})
        self.pw.check_image = mock.MagicMock(return_value=dict(
            Labels={'kolla_version': '1.0.1'}))
        self.assertTrue(self.pw.compare_labels(container_info))

    def test_compare_tmpfs_neg(self):
        container_info = {'HostConfig': dict(Tmpfs=['foo'])}
        self.pw = get_PodmanWorker({'tmpfs': ['foo']})

        self.assertFalse(self.pw.compare_tmpfs(container_info))

    def test_compare_tmpfs_neg_empty_string(self):
        container_info = {'HostConfig': dict()}
        self.pw = get_PodmanWorker({'tmpfs': ['']})

        self.assertFalse(self.pw.compare_tmpfs(container_info))

    def test_compare_tmpfs_pos_different(self):
        container_info = {'HostConfig': dict(Tmpfs=['foo'])}
        self.pw = get_PodmanWorker({'tmpfs': ['bar']})

        self.assertTrue(self.pw.compare_tmpfs(container_info))

    def test_compare_tmpfs_pos_empty_new(self):
        container_info = {'HostConfig': dict(Tmpfs=['foo'])}
        self.pw = get_PodmanWorker({})

        self.assertTrue(self.pw.compare_tmpfs(container_info))

    def test_compare_tmpfs_pos_empty_current(self):
        container_info = {'HostConfig': dict()}
        self.pw = get_PodmanWorker({'tmpfs': ['bar']})

        self.assertTrue(self.pw.compare_tmpfs(container_info))

    def test_compare_volumes_from_neg(self):
        container_info = {'HostConfig': dict(VolumesFrom=['777f7dc92da7'])}
        self.pw = get_PodmanWorker({'volumes_from': ['777f7dc92da7']})

        self.assertFalse(self.pw.compare_volumes_from(container_info))

    def test_compare_volumes_from_post(self):
        container_info = {'HostConfig': dict(VolumesFrom=['777f7dc92da7'])}
        self.pw = get_PodmanWorker({'volumes_from': ['ba8c0c54f0f2']})

        self.assertTrue(self.pw.compare_volumes_from(container_info))

    def test_compare_volumes_neg(self):
        container_info = {
            'Config': dict(Volumes=['/var/log/kolla/']),
            'HostConfig': dict(Binds=['kolla_logs:/var/log/kolla/:rw'])}
        self.pw = get_PodmanWorker(
            {'volumes': ['kolla_logs:/var/log/kolla/:rw']})

        self.assertFalse(self.pw.compare_volumes(container_info))

    def test_compare_volumes_pos(self):
        container_info = {
            'Config': dict(Volumes=['/var/log/kolla/']),
            'HostConfig': dict(Binds=['kolla_logs:/var/log/kolla/:rw'])}
        self.pw = get_PodmanWorker(
            {'volumes': ['/dev/:/dev/:rw']})

        self.assertTrue(self.pw.compare_volumes(container_info))

    def test_compare_environment_neg(self):
        container_info = {'Config': dict(
            Env=['KOLLA_CONFIG_STRATEGY=COPY_ALWAYS',
                 'KOLLA_BASE_DISTRO=ubuntu',
                 'KOLLA_INSTALL_TYPE=binary']
        )}
        self.pw = get_PodmanWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ALWAYS',
                                KOLLA_BASE_DISTRO='ubuntu',
                                KOLLA_INSTALL_TYPE='binary')})

        self.assertFalse(self.pw.compare_environment(container_info))

    def test_compare_environment_pos(self):
        container_info = {'Config': dict(
            Env=['KOLLA_CONFIG_STRATEGY=COPY_ALWAYS',
                 'KOLLA_BASE_DISTRO=ubuntu',
                 'KOLLA_INSTALL_TYPE=binary']
        )}
        self.pw = get_PodmanWorker({
            'environment': dict(KOLLA_CONFIG_STRATEGY='COPY_ALWAYS',
                                KOLLA_BASE_DISTRO='centos',
                                KOLLA_INSTALL_TYPE='binary')})

        self.assertTrue(self.pw.compare_environment(container_info))

    def test_compare_container_state_pos(self):
        container_info = {'State': dict(Status='running')}
        self.pw = get_PodmanWorker({'state': 'exited'})
        self.assertTrue(self.pw.compare_container_state(container_info))

    def test_compare_container_state_neg(self):
        container_info = {'State': dict(Status='running')}
        self.pw = get_PodmanWorker({'state': 'running'})
        self.assertFalse(self.pw.compare_container_state(container_info))

    def test_compare_dimensions_pos(self):
        self.fake_data['params']['dimensions'] = {
            'blkio_weight': 10, 'mem_limit': 30}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertTrue(self.pw.compare_dimensions(container_info))

    def test_compare_dimensions_neg(self):
        self.fake_data['params']['dimensions'] = {
            'blkio_weight': 10}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 10,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertFalse(self.pw.compare_dimensions(container_info))

    def test_compare_wrong_dimensions(self):
        self.fake_data['params']['dimensions'] = {
            'blki_weight': 0}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.pw.compare_dimensions(container_info)
        self.pw.module.exit_json.assert_called_once_with(
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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertTrue(self.pw.compare_dimensions(container_info))

    def test_compare_dimensions_removed_and_changed(self):
        self.fake_data['params']['dimensions'] = {
            'mem_reservation': 10}
        container_info = dict()
        # Here mem_limit and mem_reservation are already present
        # Now we are updating only 'mem_reservation'.
        # Ideally it should return True stating that the podman
        # dimensions have been changed.
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 10, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 10,
            'Ulimits': []}
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertTrue(self.pw.compare_dimensions(container_info))

    def test_compare_dimensions_explicit_default(self):
        self.fake_data['params']['dimensions'] = {
            'mem_reservation': 0}
        container_info = dict()
        # Here mem_limit and mem_reservation are already present
        # Now we are updating only 'mem_reservation'.
        # Ideally it should return True stating that the podman
        # dimensions have been changed.
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertFalse(self.pw.compare_dimensions(container_info))

    def test_compare_ulimits_pos(self):
        self.fake_data['params']['dimensions'] = {
            'ulimits': {'nofile': {'soft': 131072, 'hard': 131072}}}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': []}
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertTrue(self.pw.compare_dimensions(container_info))

    def test_compare_ulimits_neg(self):
        self.fake_data['params']['dimensions'] = {
            'ulimits': {'nofile': {'soft': 131072, 'hard': 131072}}}
        ulimits_nofile = {'Name': 'nofile',
                          'Soft': 131072, 'Hard': 131072}
        container_info = dict()
        container_info['HostConfig'] = {
            'CpuPeriod': 0, 'KernelMemory': 0, 'Memory': 0, 'CpuQuota': 0,
            'CpusetCpus': '', 'CpuShares': 0, 'BlkioWeight': 0,
            'CpusetMems': '', 'MemorySwap': 0, 'MemoryReservation': 0,
            'Ulimits': [ulimits_nofile]}
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertFalse(self.pw.compare_dimensions(container_info))

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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertTrue(self.pw.compare_healthcheck(container_info))

    def test_compare_empty_current_healthcheck(self):
        self.fake_data['params']['healthcheck'] = {
            'test': ['CMD-SHELL', '/bin/check.sh'],
            'interval': 30,
            'timeout': 30,
            'start_period': 5,
            'retries': 3}
        container_info = dict()
        container_info['Config'] = {}
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertTrue(self.pw.compare_healthcheck(container_info))

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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.pw.compare_healthcheck(container_info)
        self.pw.module.exit_json.assert_called_once_with(
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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertTrue(self.pw.compare_healthcheck(container_info))

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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertFalse(self.pw.compare_healthcheck(container_info))

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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertTrue(self.pw.compare_healthcheck(container_info))

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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertRaises(TypeError,
                          lambda: self.pw.compare_healthcheck(container_info))

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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertRaises(ValueError,
                          lambda: self.pw.compare_healthcheck(container_info))

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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.pw.compare_healthcheck(container_info)
        self.pw.module.exit_json.assert_called_once_with(
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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.pw.compare_healthcheck(container_info)
        self.pw.module.exit_json.assert_called_once_with(
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
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertTrue(self.pw.compare_healthcheck(container_info))

    def test_parse_healthcheck_empty(self):
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertIsNone(self.pw.parse_healthcheck(
                          self.fake_data.get('params', {}).get('healthcheck')))

    def test_parse_healthcheck_test_none(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': 'NONE'}
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertIsNone(self.pw.parse_healthcheck(
                          self.fake_data['params']['healthcheck']))

    def test_parse_healthcheck_test_none_brackets(self):
        self.fake_data['params']['healthcheck'] = \
            {'test': ['NONE']}
        self.pw = get_PodmanWorker(self.fake_data['params'])
        self.assertIsNone(self.pw.parse_healthcheck(
                          self.fake_data['params']['healthcheck']))
