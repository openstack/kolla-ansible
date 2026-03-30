# Copyright 2016 99cloud Inc.
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

import collections
import io
import json
import secrets
import tarfile
import traceback

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: kolla_toolbox
short_description: >
  Module for invoking ansible module in kolla_toolbox container.
description:
  - A module targeting at invoking ansible module in kolla_toolbox
    container as used by Kolla project.
options:
  container_engine:
    description:
      - Name of container engine to use
    required: True
    type: str
    choices: ['docker', 'podman']
  module_name:
    description:
      - The module name to invoke
    required: True
    type: str
  module_args:
    description:
      - The module args use by the module
    required: False
    type: dict
  module_extra_vars:
    description:
      - The extra variables used by the module
    required: False
    type: dict
  user:
    description:
      - The user to execute Ansible inside kolla_toolbox with
    required: False
    type: str
  api_version:
    description:
      - The version of the API for client to use when contacting container API
    required: False
    type: str
    default: auto
  timeout:
    description:
      - The default timeout for client when contacting container API
    required: False
    type: int
    default: 180
authors: Jeffrey Zhang, Roman Krček
'''

EXAMPLES = '''
- hosts: controller
  tasks:
    - name: Ensure the directory is removed
      kolla_toolbox:
        container_engine: podman
        module_name: file
        module_args:
          path: /tmp/a
          state: absent
    - name: Create mysql database
      kolla_toolbox:
        container_engine: docker
        module_name: mysql_db
        module_args:
          login_host: 192.168.1.10
          login_user: root
          login_password: admin
          name: testdb
    - name: Create default user role
      kolla_toolbox:
        container_engine: docker
        module_name: openstack.cloud.identity_role
        module_args:
          name: member
          auth: "{{ '{{ openstack_keystone_auth }}' }}"
        module_extra_vars:
          openstack_keystone_auth:
            auth_url: http://127.0.0.1:5000
            username: admin
            password: password
            project_name: "admin"
            domain_name: "default"
'''

# NOTE(mnasiadka): Full path to Python inside the kolla_toolbox container
_PYTHON = '/opt/ansible/bin/python3'

# NOTE(mnasiadka): Base directory for ansible-runner private_data_dir trees
_PDD_BASEDIR = '/var/lib/ansible'

# NOTE(mnasiadka): Script run inside kolla_toolbox to extract the terminal
#                  ansible-runner vent from job_events and print it as JSON
_PARSE_SCRIPT = """\
import json, os, sys
pdd = %r
events_dir = None
for root, dirs, files in os.walk(pdd):
    if "job_events" in dirs:
        events_dir = os.path.join(root, "job_events")
        break
if not events_dir:
    print(json.dumps({"failed": True,
                      "msg": "no job_events dir under " + pdd}))
    sys.exit(1)
terminal = {"runner_on_ok", "runner_on_failed",
            "runner_on_unreachable", "runner_on_async_failed",
            "runner_on_skipped"}
for fname in sorted(os.listdir(events_dir)):
    path = os.path.join(events_dir, fname)
    with open(path) as f:
        event = json.load(f)
    event_type = event.get("event", "")
    if event_type in terminal:
        res = event.get("event_data", {}).get("res", {})
        res.pop("_ansible_no_log", None)
        res["_runner_status"] = event_type
        print(json.dumps(res))
        sys.exit(0)
    lifecycle_events = {"runner_on_start", "runner_on_no_hosts",
                 "runner_on_async_poll", "runner_on_async_ok"}
    if event_type.startswith("runner_on_") and (
            event_type not in lifecycle_events):
        print(json.dumps({"failed": True,
                          "msg": "unhandled runner event: "
                                 + event_type}))
        sys.exit(1)
print(json.dumps({"failed": True,
                  "msg": "no terminal event found"}))
sys.exit(1)
"""


# NOTE(mnasiadka): Docker SDK exec_run returns a namedtuple with .exit_code
#                  and .output attributes, while Podman SDK returns a
#                  plain (exit_code, output) tuple.
_ExecResult = collections.namedtuple(
    '_ExecResult', ['exit_code', 'output'])


def _build_playbook(module_name, module_args, extra_vars, check_mode):
    """Return a JSON playbook string for *module_name* / *module_args*.

    Both module_args and extra_vars are embedded as dicts so they live
    on disk inside the container and never appear on any CLI.
    """
    play = {
        'name': 'kolla_toolbox',
        'hosts': 'localhost',
        'gather_facts': False,
        'tasks': [{'name': 'kolla_toolbox task',
                   module_name: module_args}],
    }
    if extra_vars:
        play['vars'] = extra_vars
    if check_mode:
        play['check_mode'] = True
    return json.dumps([play])


def _make_tar(files):
    """Build an in-memory tar from {relative_path: str|bytes}.

    Returns a BytesIO at position 0, ready for put_archive(base_dir).
    Paths are relative to the put_archive destination.
    Parent directory entries are created automatically.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tf:
        seen_dirs = set()
        for rel_path, content in files.items():
            parts = rel_path.split('/')
            for depth in range(1, len(parts)):
                dir_path = '/'.join(parts[:depth])
                if dir_path not in seen_dirs:
                    dir_info = tarfile.TarInfo(name=dir_path)
                    dir_info.type = tarfile.DIRTYPE
                    dir_info.mode = 0o755
                    tf.addfile(dir_info)
                    seen_dirs.add(dir_path)
            encoded = (content if isinstance(content, bytes)
                       else content.encode('utf-8'))
            info = tarfile.TarInfo(name=rel_path)
            info.size = len(encoded)
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(encoded))
    buf.seek(0)
    return buf


def _exec_run(container, cmd, **kwargs):
    """Normalise exec_run return value across Docker and Podman SDKs.

    Docker SDK returns an ExecResult namedtuple with .exit_code and
    .output attributes. Podman SDK returns a plain (exit_code, output)
    tuple. This wrapper always returns an _ExecResult namedtuple.

    tty=True is forced so output is a plain byte stream with no
    multiplexed frame headers, avoiding the need to parse the
    Docker/Podman mux format.
    """
    kwargs['tty'] = True

    result = container.exec_run(cmd, **kwargs)
    if isinstance(result, tuple):
        return _ExecResult(*result)
    return _ExecResult(result.exit_code, result.output)


class KollaToolboxWorker():
    def __init__(self, module, client, container_errors) -> None:
        self.module = module
        self.client = client
        self.container_errors = container_errors
        self.result = dict()

    def _get_toolbox_container(self):
        """Get the kolla_toolbox container object, if up and running."""
        cont = self.client.containers.list(
            filters=dict(name='kolla_toolbox', status='running')
        )
        if not cont:
            self.module.fail_json(
                msg='kolla_toolbox container is missing or not running!'
            )
        return cont[0]

    def _push_private_data_dir(self, kolla_toolbox, pdd, user):
        """Push the ansible-runner private_data_dir tree into container.

        Creates pdd (and pdd/tmp for Ansible's temp files) as root, then
        chowns both to *user* if specified so ansible-runner can write
        there even when the user has no shell (e.g. rabbitmq, nova).

        Pushes inventory and playbook via a single put_archive() call —
        one tar stream through the socket, no secrets in any argv.
        """
        params = self.module.params

        playbook_json = _build_playbook(
            params['module_name'],
            params.get('module_args') or {},
            params.get('module_extra_vars') or {},
            self.module.check_mode,
        )

        # NOTE(mnasiadka): Build and run the setup script as root so it
        #                  can always write to _PDD_BASEDIR.
        #                  Chown pdd to the effective exec user
        #                  so ansible-runner can create artifacts/.
        chown_user = user if user else 'ansible'
        if chown_user == 'root':
            setup = (
                'import os\n'
                'for p in [%r, %r + "/tmp"]:\n'
                '    os.makedirs(p, exist_ok=True)\n'
            ) % (pdd, pdd)
        else:
            setup = (
                'import os, pwd\n'
                'pw = pwd.getpwnam(%r)\n'
                'for p in [%r, %r + "/tmp"]:\n'
                '    os.makedirs(p, exist_ok=True)\n'
                '    os.chown(p, pw.pw_uid, pw.pw_gid)\n'
            ) % (chown_user, pdd, pdd)

        mkdir_result = _exec_run(
            kolla_toolbox, [_PYTHON, '-c', setup], user='root')
        if mkdir_result.exit_code != 0:
            self.module.fail_json(
                msg='Failed to create pdd %s in kolla_toolbox: %s'
                    % (pdd, mkdir_result.output.decode(errors='replace'))
            )

        inventory = (
            'localhost'
            ' ansible_connection=local'
            ' ansible_remote_tmp={pdd}/tmp'
            ' ansible_local_tmp={pdd}/tmp'
            ' ansible_local_temp={pdd}/tmp'
            ' ansible_python_interpreter={python}\n'
        ).format(pdd=pdd, python=_PYTHON)

        kolla_toolbox.put_archive(pdd, _make_tar({
            'inventory/hosts': inventory,
            'project/main.json': playbook_json,
        }))

    def _parse_runner_result(self, kolla_toolbox, pdd, user):
        """Extract the module result from ansible-runner job_events.

        Runs _PARSE_SCRIPT inside the container via exec_run: it walks
        job_events, finds the terminal event, and prints result as JSON.
        No tar parsing, no path-prefix assumptions.
        """
        parse_kwargs = {}
        if user:
            parse_kwargs['user'] = user

        result = _exec_run(
            kolla_toolbox, [_PYTHON, '-c', _PARSE_SCRIPT % pdd],
            **parse_kwargs
        )

        if result.exit_code != 0:
            self.module.fail_json(
                msg='Failed to read ansible-runner result (exit %d): %s'
                    % (result.exit_code,
                       result.output.decode(errors='replace'))
            )

        try:
            res = json.loads(result.output.decode('utf-8'))
        except json.JSONDecodeError:
            self.module.fail_json(
                msg='Could not parse ansible-runner result output: %r'
                    % result.output
            )

        status = res.pop('_runner_status', 'runner_on_ok')
        res.pop('_ansible_no_log', None)
        if res.get('failed') or status not in ['runner_on_ok',
                                               'runner_on_skipped']:
            msg = res.pop(
                'msg',
                'Module execution failed inside kolla_toolbox'
            )
            self.module.fail_json(msg=msg, **res)

        return res

    def main(self) -> None:
        """Run the requested module inside the kolla_toolbox container.

        1. Generate a unique pdd name on the controller (no exec).
        2. Push inventory + playbook via put_archive (secrets travel as
           tar content, never in argv).
        3. Run ansible-runner CLI (only pdd path in argv, no secrets).
        4. Extract result via _PARSE_SCRIPT exec (walks job_events,
           prints terminal event as JSON — no tar, no path assumptions).
        5. Clean up pdd unconditionally in finally.
        """
        kolla_toolbox = self._get_toolbox_container()
        user = self.module.params.get('user')

        check_runner = _exec_run(
            kolla_toolbox, ['test', '-x', '/opt/ansible/bin/ansible-runner'])
        if check_runner.exit_code != 0:
            self.module.fail_json(
                msg="The 'ansible-runner' binary was not found in the "
                    "kolla_toolbox container. Please ensure the container "
                    "image is up to date and includes ansible-runner."
            )

        # NOTE(mnasiadka): Generate a unique pdd name without creating
        #                  anything locally.
        pdd = _PDD_BASEDIR + '/kolla_runner.' + secrets.token_urlsafe(8)

        try:
            self._push_private_data_dir(kolla_toolbox, pdd, user)

            runner_env = {}
            if self.module._diff:
                runner_env['ANSIBLE_DIFF_MODE'] = '1'

            runner_result = _exec_run(
                kolla_toolbox,
                ['/opt/ansible/bin/ansible-runner', 'run', pdd,
                 '--playbook', 'main.json',
                 '--rotate-artifacts', '1'],
                user=user,
                environment=runner_env
            )
            # exit 2 = task failed/unreachable; handled via event below.
            # Anything else is a runner-level failure.
            if runner_result.exit_code not in (0, 2):
                self.module.fail_json(
                    msg='ansible-runner exited with code %d: %s'
                        % (runner_result.exit_code,
                           runner_result.output.decode(errors='replace'))
                )

            self.result = self._parse_runner_result(
                kolla_toolbox, pdd, user)

        finally:
            _exec_run(
                kolla_toolbox,
                [_PYTHON, '-c',
                 'import shutil; shutil.rmtree(%r, ignore_errors=True)'
                 % pdd],
                user='root',
            )


def create_container_client(module: AnsibleModule):
    """Return container engine client based on the parameters."""
    container_engine = module.params.get('container_engine')
    api_version = module.params.get('api_version')
    timeout = module.params.get('timeout')

    if container_engine == 'docker':
        try:
            import docker
            import docker.errors as container_errors
        except ImportError:
            module.fail_json(
                msg='The docker library could not be imported!'
            )
        client = docker.DockerClient(
            base_url='http+unix:/var/run/docker.sock',
            version=api_version,
            timeout=timeout)
    else:
        try:
            import podman
            import podman.errors as container_errors
        except ImportError:
            module.fail_json(
                msg='The podman library could not be imported!'
            )
        # NOTE(r-krcek): PodmanClient has a glitch in which when you pass
        # 'auto' to api_version, it literally creates an url of /vauto
        # for API calls, instead of actually finding the compatible version
        # like /v5.0.0, this leads to 404 Error when accessing the API.
        if api_version == 'auto':
            client = podman.PodmanClient(
                base_url='http+unix:/run/podman/podman.sock',
                timeout=timeout)
        else:
            client = podman.PodmanClient(
                base_url='http+unix:/run/podman/podman.sock',
                version=api_version,
                timeout=timeout)
    return client, container_errors


class KollaAnsibleModule(AnsibleModule):
    """AnsibleModule subclass that redacts known sensitive keys

    Overrides _log_invocation() to add sensitive values to
    no_log_values before the "Invoked with ..." syslog message
    is written, allowing the rest of module_args to remain
    visible for debugging.
    """

    _NO_LOG_KEYS = frozenset({'auth', 'login_password', 'password'})

    def _log_invocation(self):
        for param in ('module_args', 'module_extra_vars'):
            for key, value in (self.params.get(param) or {}).items():
                if key in self._NO_LOG_KEYS and value is not None:
                    self.no_log_values.add(str(value))
        super()._log_invocation()


def create_ansible_module() -> KollaAnsibleModule:
    argument_spec = dict(
        container_engine=dict(type='str',
                              choices=['podman', 'docker'],
                              required=True),
        module_name=dict(type='str', required=True),
        module_args=dict(type='dict', default=dict()),
        module_extra_vars=dict(type='dict', default=dict()),
        api_version=dict(type='str', default='auto'),
        timeout=dict(type='int', default=180),
        user=dict(type='str'),
    )

    return KollaAnsibleModule(argument_spec=argument_spec,
                              supports_check_mode=True)


def main():
    module = create_ansible_module()
    client, container_errors = create_container_client(module)
    ktbw = KollaToolboxWorker(module, client, container_errors)

    try:
        ktbw.main()
        module.exit_json(**ktbw.result)
    except Exception:
        module.fail_json(changed=True,
                         msg=traceback.format_exc())


if __name__ == '__main__':
    main()
