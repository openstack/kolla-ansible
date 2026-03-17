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
import io
import json
import os
import sys
import tarfile

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


def _tar_contents(tar_bytes):
    """Return {member_name: bytes} for all files in a tar stream."""
    result = {}
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode='r') as tf:
        for member in tf.getmembers():
            if member.isfile():
                result[member.name] = tf.extractfile(member).read()
    return result


def _make_exec_result(exit_code, output, as_tuple=False):
    """Return an exec result compatible with _exec_run normalisation.

    Use as_tuple=True to simulate the Podman SDK plain-tuple return.
    """
    raw = (output if isinstance(output, bytes)
           else output.encode('utf-8'))
    if as_tuple:
        return (exit_code, raw)
    return kolla_toolbox._ExecResult(exit_code, raw)


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
        self.mock_ansible_module.check_mode = False

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

    def test_exec_run_normalises_docker_namedtuple(self):
        """Docker SDK returns namedtuple — _exec_run must pass it through."""
        container = mock.MagicMock()
        container.exec_run.return_value = kolla_toolbox._ExecResult(0, b'ok')

        result = kolla_toolbox._exec_run(container, ['echo'])

        self.assertEqual(0, result.exit_code)
        self.assertEqual(b'ok', result.output)

    def test_exec_run_normalises_podman_tuple(self):
        """Podman SDK returns plain tuple — _exec_run must normalise it."""
        container = mock.MagicMock()
        container.exec_run.return_value = (0, b'ok')

        result = kolla_toolbox._exec_run(container, ['echo'])

        self.assertEqual(0, result.exit_code)
        self.assertEqual(b'ok', result.output)


class TestBuildPlaybook(base.BaseTestCase):
    """Tests for the _build_playbook helper."""

    def test_module_args_embedded_as_dict_not_string(self):
        """args must be a dict in the playbook, not in proc argv"""
        module_args = {'password': 'S3cr3t', 'user': 'admin'}  # nosec B105
        result = json.loads(
            kolla_toolbox._build_playbook(
                'community.mysql.mysql_user', module_args, {}, False))

        task = result[0]['tasks'][0]
        task_args = task['community.mysql.mysql_user']
        # Must be a dict, not a string
        self.assertIsInstance(task_args, dict)
        self.assertEqual(module_args, task_args)
        # The password must not appear as a bare string anywhere in the
        # serialised playbook outside of the JSON-encoded dict value
        playbook_str = json.dumps(result)
        # It appears once, inside the dict — not as a CLI token
        self.assertNotIn("password='S3cr3t'", playbook_str)

    def test_extra_vars_under_play_vars(self):
        extra_vars = {'db_host': 'localhost', 'db_port': 3306}
        result = json.loads(
            kolla_toolbox._build_playbook('ping', {}, extra_vars, False))

        self.assertEqual(extra_vars, result[0]['vars'])

    def test_empty_extra_vars_not_in_play(self):
        result = json.loads(
            kolla_toolbox._build_playbook('ping', {}, {}, False))

        self.assertNotIn('vars', result[0])

    def test_check_mode_sets_play_check_mode(self):
        result = json.loads(
            kolla_toolbox._build_playbook('ping', {}, {}, True))

        self.assertTrue(result[0]['check_mode'])

    def test_check_mode_false_not_in_play(self):
        result = json.loads(
            kolla_toolbox._build_playbook('ping', {}, {}, False))

        self.assertNotIn('check_mode', result[0])

    def test_module_name_is_task_key(self):
        result = json.loads(
            kolla_toolbox._build_playbook(
                'community.mysql.mysql_db', {}, {}, False))

        task = result[0]['tasks'][0]
        self.assertIn('community.mysql.mysql_db', task)


class TestMakeTar(base.BaseTestCase):
    """Tests for the _make_tar helper."""

    def test_files_present_with_correct_content(self):
        files = {
            'inventory/hosts': 'localhost\n',
            'project/main.json': '{"play": 1}',
        }
        tar_bytes = kolla_toolbox._make_tar(files).read()
        contents = _tar_contents(tar_bytes)

        self.assertEqual(b'localhost\n', contents['inventory/hosts'])
        self.assertEqual(b'{"play": 1}', contents['project/main.json'])

    def test_parent_directories_created(self):
        files = {'a/b/c/file.txt': 'data'}
        tar_bytes = kolla_toolbox._make_tar(files).read()

        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode='r') as tf:
            names = tf.getnames()

        self.assertIn('a', names)
        self.assertIn('a/b', names)
        self.assertIn('a/b/c', names)
        self.assertIn('a/b/c/file.txt', names)

    def test_bytes_content_not_double_encoded(self):
        files = {'file.bin': b'\x00\x01\x02'}
        tar_bytes = kolla_toolbox._make_tar(files).read()
        contents = _tar_contents(tar_bytes)

        self.assertEqual(b'\x00\x01\x02', contents['file.bin'])

    def test_returned_bytesio_at_position_zero(self):
        buf = kolla_toolbox._make_tar({'f': 'x'})
        self.assertEqual(0, buf.tell())


class TestPushPrivateDataDir(TestKollaToolboxModule):
    """Tests for KollaToolboxWorker._push_private_data_dir."""

    def setUp(self):
        super().setUp()
        self.mock_ansible_module = mock.MagicMock()
        self.mock_ansible_module.fail_json.side_effect = self.fail_json
        self.mock_ansible_module.check_mode = False
        self.mock_ansible_module.params = {
            'module_name': 'community.mysql.mysql_user',
            'module_args': {'user': 'admin',
                            'password': 'S3cr3t'},  # nosec B105
            'module_extra_vars': {},
        }
        self.mock_container_errors = mock.MagicMock()
        self.fake_ktbw = kolla_toolbox.KollaToolboxWorker(
            self.mock_ansible_module,
            mock.MagicMock(),
            self.mock_container_errors)

        self.mock_container = mock.MagicMock()
        self.mock_container.exec_run.return_value = _make_exec_result(
            0, b'')  # makedirs
        self.pdd = '/var/lib/ansible/kolla_runner.test1'

    def _get_put_archive_tar(self):
        """Return the tar bytes passed to put_archive."""
        call_args = self.mock_container.put_archive.call_args
        tar_arg = call_args.args[1]  # second positional arg
        return tar_arg.read()

    def test_secrets_not_in_exec_argv(self):
        """module_args values must not appear in any exec_run argv."""
        self.fake_ktbw._push_private_data_dir(
            self.mock_container, self.pdd, None)

        for call in self.mock_container.exec_run.call_args_list:
            argv = call[0][0]  # first positional arg is the command list
            argv_str = ' '.join(str(a) for a in argv)
            self.assertNotIn('S3cr3t', argv_str)
            self.assertNotIn('admin', argv_str)

    def test_module_args_in_tar_as_dict(self):
        """module_args must be a dict in the pushed playbook, not a string."""
        self.fake_ktbw._push_private_data_dir(
            self.mock_container, self.pdd, None)

        tar_bytes = self._get_put_archive_tar()
        contents = _tar_contents(tar_bytes)
        playbook = json.loads(contents['project/main.json'])
        task_args = playbook[0]['tasks'][0]['community.mysql.mysql_user']

        self.assertIsInstance(task_args, dict)
        self.assertEqual('S3cr3t', task_args['password'])

    def test_inventory_contains_required_vars(self):
        self.fake_ktbw._push_private_data_dir(
            self.mock_container, self.pdd, None)

        tar_bytes = self._get_put_archive_tar()
        contents = _tar_contents(tar_bytes)
        inventory = contents['inventory/hosts'].decode()

        self.assertIn('ansible_connection=local', inventory)
        self.assertIn('ansible_remote_tmp=', inventory)
        self.assertIn('ansible_local_tmp=', inventory)
        self.assertIn('ansible_python_interpreter=', inventory)
        self.assertIn(kolla_toolbox._PYTHON, inventory)

    def test_setup_exec_chown_to_ansible_when_user_is_none(self):
        self.fake_ktbw._push_private_data_dir(
            self.mock_container, self.pdd, None)

        setup_call = self.mock_container.exec_run.call_args_list[0]
        script = setup_call[0][0][2]  # python3 -c <script>
        self.assertIn('chown', script)
        self.assertIn('ansible', script)

    def test_setup_exec_no_chown_when_user_is_root(self):
        self.fake_ktbw._push_private_data_dir(
            self.mock_container, self.pdd, 'root')

        setup_call = self.mock_container.exec_run.call_args_list[0]
        script = setup_call[0][0][2]
        self.assertNotIn('chown', script)

    def test_setup_exec_chown_for_non_root_user(self):
        self.fake_ktbw._push_private_data_dir(
            self.mock_container, self.pdd, 'rabbitmq')

        setup_call = self.mock_container.exec_run.call_args_list[0]
        script = setup_call[0][0][2]
        self.assertIn('chown', script)
        self.assertIn('rabbitmq', script)

    def test_fail_json_when_setup_exec_fails(self):
        self.mock_container.exec_run.return_value = _make_exec_result(
            1, b'Permission denied')  # makedirs

        error = self.assertRaises(
            AnsibleFailJson,
            self.fake_ktbw._push_private_data_dir,
            self.mock_container, self.pdd, None)

        self.assertIn('Failed to create pdd', error.result['msg'])
        # put_archive must not be called after setup failure
        self.mock_container.put_archive.assert_not_called()

    def test_put_archive_called_with_pdd(self):
        self.fake_ktbw._push_private_data_dir(
            self.mock_container, self.pdd, None)

        self.mock_container.put_archive.assert_called_once()
        call_path = self.mock_container.put_archive.call_args.args[0]
        self.assertEqual(self.pdd, call_path)


class TestParseRunnerResult(TestKollaToolboxModule):
    """Tests for KollaToolboxWorker._parse_runner_result."""

    def setUp(self):
        super().setUp()
        self.mock_ansible_module = mock.MagicMock()
        self.mock_ansible_module.fail_json.side_effect = self.fail_json
        self.fake_ktbw = kolla_toolbox.KollaToolboxWorker(
            self.mock_ansible_module,
            mock.MagicMock(),
            mock.MagicMock())
        self.mock_container = mock.MagicMock()
        self.pdd = '/var/lib/ansible/kolla_runner.test1'

    def _result_output(self, event_type, res):
        res['_runner_status'] = event_type
        return json.dumps(res).encode('utf-8')

    def test_returns_result_on_runner_on_ok(self):
        expected = {'changed': False, 'ping': 'pong'}
        self.mock_container.exec_run.return_value = _make_exec_result(
            # _PARSE_SCRIPT
            0, self._result_output('runner_on_ok', expected.copy()))

        result = self.fake_ktbw._parse_runner_result(
            self.mock_container, self.pdd, None)

        self.assertEqual(expected, result)

    def test_fail_json_on_runner_on_failed(self):
        self.mock_container.exec_run.return_value = _make_exec_result(
            0, self._result_output(
                'runner_on_failed', {'msg': 'Access denied'}))  # _PARSE_SCRIPT

        error = self.assertRaises(
            AnsibleFailJson,
            self.fake_ktbw._parse_runner_result,
            self.mock_container, self.pdd, None)

        self.assertIn('Access denied', error.result['msg'])

    def test_fail_json_on_runner_on_unreachable(self):
        self.mock_container.exec_run.return_value = _make_exec_result(
            0, self._result_output(
                'runner_on_unreachable',
                {'msg': 'Host unreachable'}))  # _PARSE_SCRIPT

        error = self.assertRaises(
            AnsibleFailJson,
            self.fake_ktbw._parse_runner_result,
            self.mock_container, self.pdd, None)

        self.assertIn('Host unreachable', error.result['msg'])

    def test_ansible_no_log_stripped(self):
        res = {'changed': True, '_ansible_no_log': True, 'key': 'val'}
        self.mock_container.exec_run.return_value = _make_exec_result(
            0, self._result_output('runner_on_ok', res))  # _PARSE_SCRIPT

        result = self.fake_ktbw._parse_runner_result(
            self.mock_container, self.pdd, None)

        self.assertNotIn('_ansible_no_log', result)
        self.assertEqual('val', result['key'])

    def test_fail_json_on_nonzero_exit_code(self):
        self.mock_container.exec_run.return_value = _make_exec_result(
            1, b'something went wrong')  # _PARSE_SCRIPT

        error = self.assertRaises(
            AnsibleFailJson,
            self.fake_ktbw._parse_runner_result,
            self.mock_container, self.pdd, None)

        self.assertIn('Failed to read ansible-runner result',
                      error.result['msg'])

    def test_fail_json_on_invalid_json_output(self):
        self.mock_container.exec_run.return_value = _make_exec_result(
            0, b'not valid json')  # _PARSE_SCRIPT

        error = self.assertRaises(
            AnsibleFailJson,
            self.fake_ktbw._parse_runner_result,
            self.mock_container, self.pdd, None)

        self.assertIn('Could not parse ansible-runner result output',
                      error.result['msg'])

    def test_user_passed_to_exec_run_when_specified(self):
        res = {'changed': False}
        self.mock_container.exec_run.return_value = _make_exec_result(
            0, self._result_output('runner_on_ok', res))  # _PARSE_SCRIPT

        self.fake_ktbw._parse_runner_result(
            self.mock_container, self.pdd, 'rabbitmq')

        call_kwargs = self.mock_container.exec_run.call_args.kwargs
        self.assertEqual('rabbitmq', call_kwargs.get('user'))

    def test_user_not_passed_to_exec_run_when_none(self):
        res = {'changed': False}
        self.mock_container.exec_run.return_value = _make_exec_result(
            0, self._result_output('runner_on_ok', res))  # _PARSE_SCRIPT

        self.fake_ktbw._parse_runner_result(
            self.mock_container, self.pdd, None)

        call_kwargs = self.mock_container.exec_run.call_args.kwargs
        self.assertNotIn('user', call_kwargs)


class TestKollaToolboxWorkerMain(TestKollaToolboxModule):
    """Tests for KollaToolboxWorker.main."""

    def setUp(self):
        super().setUp()
        self.mock_ansible_module = mock.MagicMock()
        self.mock_ansible_module.fail_json.side_effect = self.fail_json
        self.mock_ansible_module.check_mode = False
        self.mock_ansible_module.params = {
            'module_name': 'ping',
            'module_args': {},
            'module_extra_vars': {},
            'user': None,
        }
        self.mock_container_client = mock.MagicMock()
        self.mock_container_errors = mock.MagicMock()
        self.fake_ktbw = kolla_toolbox.KollaToolboxWorker(
            self.mock_ansible_module,
            self.mock_container_client,
            self.mock_container_errors)

        self.mock_container = mock.MagicMock()
        self.mock_container_client.containers.list.return_value = [
            self.mock_container]
        # Default: setup exec succeeds, runner exits 0, parse returns ok
        ok_result = json.dumps(
            {'changed': False, '_runner_status': 'runner_on_ok'}
        ).encode()
        self.mock_container.exec_run.side_effect = [
            _make_exec_result(0, b''),   # test -x ansible-runner
            _make_exec_result(0, b''),   # makedirs
            _make_exec_result(0, b''),   # ansible-runner
            _make_exec_result(0, ok_result),  # _PARSE_SCRIPT
            _make_exec_result(0, b''),   # cleanup
        ]

    def test_pdd_under_pdd_basedir(self):
        """pdd must be under _PDD_BASEDIR, not /tmp."""
        pdd_used = []

        def capture_push(container, pdd, user):
            pdd_used.append(pdd)
            # Simulate success without real put_archive
            container.put_archive = mock.MagicMock()

        with mock.patch.object(self.fake_ktbw,
                               '_push_private_data_dir',
                               side_effect=capture_push), \
             mock.patch.object(self.fake_ktbw,
                               '_parse_runner_result',
                               return_value={'changed': False}):
            self.fake_ktbw.main()

        self.assertTrue(
            pdd_used[0].startswith('/var/lib/ansible'))

    def test_cleanup_called_on_success(self):
        ok_result = json.dumps(
            {'changed': False, '_runner_status': 'runner_on_ok'}
        ).encode()
        self.mock_container.exec_run.side_effect = [
            _make_exec_result(0, b''),  # test -x ansible-runner
            _make_exec_result(0, b''),  # makedirs
            _make_exec_result(0, b''),  # ansible-runner
            _make_exec_result(0, ok_result),  # _PARSE_SCRIPT
            _make_exec_result(0, b''),  # cleanup
        ]

        with mock.patch.object(self.fake_ktbw,
                               '_parse_runner_result',
                               return_value={'changed': False}):
            self.fake_ktbw.main()

        # Last exec_run call must be the shutil.rmtree cleanup
        last_call = self.mock_container.exec_run.call_args_list[-1]
        last_cmd = last_call[0][0]
        self.assertIn('shutil', last_cmd[-1])
        self.assertIn('rmtree', last_cmd[-1])

    def test_cleanup_called_on_failure(self):
        """finally block must run cleanup even when ansible-runner fails."""
        self.mock_container.exec_run.side_effect = [
            _make_exec_result(0, b''),  # test -x ansible-runner
            _make_exec_result(0, b''),   # makedirs
            _make_exec_result(1, b'runner crashed'),  # ansible-runner
            _make_exec_result(0, b''),   # cleanup
        ]

        self.assertRaises(AnsibleFailJson, self.fake_ktbw.main)

        last_call = self.mock_container.exec_run.call_args_list[-1]
        last_cmd = last_call[0][0]
        self.assertIn('rmtree', last_cmd[-1])

    def test_fail_json_on_runner_exit_code_other_than_0_or_2(self):
        self.mock_container.exec_run.side_effect = [
            _make_exec_result(0, b''),  # test -x ansible-runner
            _make_exec_result(0, b''),  # makedirs
            _make_exec_result(4, b'runner internal error'),  # ansible-runner
            _make_exec_result(0, b''),  # cleanup
        ]

        error = self.assertRaises(AnsibleFailJson, self.fake_ktbw.main)
        self.assertIn('ansible-runner exited with code 4',
                      error.result['msg'])

    def test_runner_exit_code_2_is_not_fatal(self):
        """Exit code 2 means task failed — we handle it via the event."""
        failed_result = json.dumps(
            {'changed': False, 'msg': 'task failed',
             '_runner_status': 'runner_on_failed'}
        ).encode()
        self.mock_container.exec_run.side_effect = [
            _make_exec_result(0, b''),  # test -x ansible-runner
            _make_exec_result(0, b''),  # makedirs
            _make_exec_result(2, b''),  # ansible-runner
            _make_exec_result(0, failed_result),  # _PARSE_SCRIPT
            _make_exec_result(0, b''),  # cleanup
        ]

        with mock.patch.object(
                self.fake_ktbw,
                '_parse_runner_result',
                side_effect=AnsibleFailJson({'msg': 'task failed'})):
            error = self.assertRaises(AnsibleFailJson, self.fake_ktbw.main)
        self.assertIn('task failed', error.result['msg'])

    def test_fail_json_when_ansible_runner_not_found(self):
        """test -x failing means ansible-runner is missing."""
        self.mock_container.exec_run.side_effect = [
            _make_exec_result(1, b''),  # test -x ansible-runner fails
            _make_exec_result(0, b''),  # cleanup
        ]

        error = self.assertRaises(AnsibleFailJson,
                                  self.fake_ktbw.main)
        self.assertIn('ansible-runner', error.result['msg'])


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
