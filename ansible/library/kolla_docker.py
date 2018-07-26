#!/usr/bin/env python

# Copyright 2015 Sam Yaple
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

DOCUMENTATION = '''
---
module: kolla_docker
short_description: Module for controlling Docker
description:
     - A module targeting at controlling Docker as used by Kolla.
options:
  common_options:
    description:
      - A dict containing common params such as login info
    required: False
    type: dict
    default: dict()
  action:
    description:
      - The action the module should take
    required: True
    type: str
    choices:
      - compare_container
      - compare_image
      - create_volume
      - get_container_env
      - get_container_state
      - pull_image
      - remove_container
      - remove_volume
      - recreate_or_restart_container
      - restart_container
      - start_container
      - stop_container
  api_version:
    description:
      - The version of the api for docker-py to use when contacting docker
    required: False
    type: str
    default: auto
  auth_email:
    description:
      - The email address used to authenticate
    required: False
    type: str
  auth_password:
    description:
      - The password used to authenticate
    required: False
    type: str
  auth_registry:
    description:
      - The registry to authenticate
    required: False
    type: str
  auth_username:
    description:
      - The username used to authenticate
    required: False
    type: str
  detach:
    description:
      - Detach from the container after it is created
    required: False
    default: True
    type: bool
  name:
    description:
      - Name of the container or volume to manage
    required: False
    type: str
  environment:
    description:
      - The environment to set for the container
    required: False
    type: dict
  image:
    description:
      - Name of the docker image
    required: False
    type: str
  ipc_mode:
    description:
      - Set docker ipc namespace
    required: False
    type: str
    default: None
    choices:
      - host
  cap_add:
    description:
      - Add capabilities to docker container
    required: False
    type: list
    default: list()
  security_opt:
    description:
      - Set container security profile
    required: False
    type: list
    default: list()
  labels:
    description:
      - List of labels to apply to container
    required: False
    type: dict
    default: dict()
  pid_mode:
    description:
      - Set docker pid namespace
    required: False
    type: str
    default: None
    choices:
      - host
  privileged:
    description:
      - Set the container to privileged
    required: False
    default: False
    type: bool
  remove_on_exit:
    description:
      - When not detaching from container, remove on successful exit
    required: False
    default: True
    type: bool
  restart_policy:
    description:
      - Determine what docker does when the container exits
    required: False
    type: str
    choices:
      - never
      - on-failure
      - always
      - unless-stopped
  restart_retries:
    description:
      - How many times to attempt a restart if restart_policy is set
    type: int
    default: 10
  volumes:
    description:
      - Set volumes for docker to use
    required: False
    type: list
  volumes_from:
    description:
      - Name or id of container(s) to use volumes from
    required: True
    type: list
  state:
    description:
      - Check container status
    required: False
    type: str
    choices:
      - running
      - exited
      - paused
author: Sam Yaple
'''

EXAMPLES = '''
- hosts: kolla_docker
  tasks:
    - name: Start container
      kolla_docker:
        image: ubuntu
        name: test_container
        action: start_container
    - name: Remove container
      kolla_docker:
        name: test_container
        action: remove_container
    - name: Pull image without starting container
      kolla_docker:
        action: pull_image
        image: private-registry.example.com:5000/ubuntu
    - name: Create named volume
        action: create_volume
        name: name_of_volume
    - name: Remove named volume
        action: remove_volume
        name: name_of_volume
'''

import json
import os
import traceback

import docker


def get_docker_client():
    return docker.APIClient


class DockerWorker(object):

    def __init__(self, module):
        self.module = module
        self.params = self.module.params
        self.changed = False

        # TLS not fully implemented
        # tls_config = self.generate_tls()

        options = {
            'version': self.params.get('api_version')
        }

        self.dc = get_docker_client()(**options)

    def generate_tls(self):
        tls = {'verify': self.params.get('tls_verify')}
        tls_cert = self.params.get('tls_cert'),
        tls_key = self.params.get('tls_key'),
        tls_cacert = self.params.get('tls_cacert')

        if tls['verify']:
            if tls_cert:
                self.check_file(tls_cert)
                self.check_file(tls_key)
                tls['client_cert'] = (tls_cert, tls_key)
            if tls_cacert:
                self.check_file(tls_cacert)
                tls['verify'] = tls_cacert

        return docker.tls.TLSConfig(**tls)

    def check_file(self, path):
        if not os.path.isfile(path):
            self.module.fail_json(
                failed=True,
                msg='There is no file at "{}"'.format(path)
            )
        if not os.access(path, os.R_OK):
            self.module.fail_json(
                failed=True,
                msg='Permission denied for file at "{}"'.format(path)
            )

    def check_image(self):
        find_image = ':'.join(self.parse_image())
        for image in self.dc.images():
            repo_tags = image.get('RepoTags')
            if not repo_tags:
                continue
            for image_name in repo_tags:
                if image_name == find_image:
                    return image

    def check_volume(self):
        for vol in self.dc.volumes()['Volumes'] or list():
            if vol['Name'] == self.params.get('name'):
                return vol

    def check_container(self):
        find_name = '/{}'.format(self.params.get('name'))
        for cont in self.dc.containers(all=True):
            if find_name in cont['Names']:
                return cont

    def get_container_info(self):
        container = self.check_container()
        if not container:
            return None
        return self.dc.inspect_container(self.params.get('name'))

    def compare_container(self):
        container = self.check_container()
        if not container or self.check_container_differs():
            self.changed = True
        return self.changed

    def check_container_differs(self):
        container_info = self.get_container_info()
        return (
            self.compare_cap_add(container_info) or
            self.compare_security_opt(container_info) or
            self.compare_image(container_info) or
            self.compare_ipc_mode(container_info) or
            self.compare_labels(container_info) or
            self.compare_privileged(container_info) or
            self.compare_pid_mode(container_info) or
            self.compare_volumes(container_info) or
            self.compare_volumes_from(container_info) or
            self.compare_environment(container_info) or
            self.compare_container_state(container_info) or
            self.compare_dimensions(container_info)
        )

    def compare_ipc_mode(self, container_info):
        new_ipc_mode = self.params.get('ipc_mode')
        current_ipc_mode = container_info['HostConfig'].get('IpcMode')
        if not current_ipc_mode:
            current_ipc_mode = None

        # only check IPC mode if it is specified
        if new_ipc_mode is not None and new_ipc_mode != current_ipc_mode:
            return True
        return False

    def compare_cap_add(self, container_info):
        new_cap_add = self.params.get('cap_add', list())
        current_cap_add = container_info['HostConfig'].get('CapAdd',
                                                           list())
        if not current_cap_add:
            current_cap_add = list()
        if set(new_cap_add).symmetric_difference(set(current_cap_add)):
            return True

    def compare_security_opt(self, container_info):
        ipc_mode = self.params.get('ipc_mode')
        pid_mode = self.params.get('pid_mode')
        privileged = self.params.get('privileged', False)
        # NOTE(jeffrey4l) security opt is disabled when using host ipc mode or
        # host pid mode or privileged. So no need to compare security opts
        if ipc_mode == 'host' or pid_mode == 'host' or privileged:
            return False
        new_sec_opt = self.params.get('security_opt', list())
        current_sec_opt = container_info['HostConfig'].get('SecurityOpt',
                                                           list())
        if not current_sec_opt:
            current_sec_opt = list()
        if set(new_sec_opt).symmetric_difference(set(current_sec_opt)):
            return True

    def compare_pid_mode(self, container_info):
        new_pid_mode = self.params.get('pid_mode')
        current_pid_mode = container_info['HostConfig'].get('PidMode')
        if not current_pid_mode:
            current_pid_mode = None

        if new_pid_mode != current_pid_mode:
            return True

    def compare_privileged(self, container_info):
        new_privileged = self.params.get('privileged')
        current_privileged = container_info['HostConfig']['Privileged']
        if new_privileged != current_privileged:
            return True

    def compare_image(self, container_info=None):
        container_info = container_info or self.get_container_info()
        parse_repository_tag = docker.utils.parse_repository_tag
        if not container_info:
            return True
        new_image = self.check_image()
        current_image = container_info['Image']
        if not new_image:
            return True
        if new_image['Id'] != current_image:
            return True
        # NOTE(Jeffrey4l) when new image and the current image have
        # the same id, but the tag name different.
        elif (parse_repository_tag(container_info['Config']['Image']) !=
              parse_repository_tag(self.params.get('image'))):
            return True

    def compare_labels(self, container_info):
        new_labels = self.params.get('labels')
        current_labels = container_info['Config'].get('Labels', dict())
        image_labels = self.check_image().get('Labels', dict())
        for k, v in image_labels.items():
            if k in new_labels:
                if v != new_labels[k]:
                    return True
            else:
                del current_labels[k]

        if new_labels != current_labels:
            return True

    def compare_volumes_from(self, container_info):
        new_vols_from = self.params.get('volumes_from')
        current_vols_from = container_info['HostConfig'].get('VolumesFrom')
        if not new_vols_from:
            new_vols_from = list()
        if not current_vols_from:
            current_vols_from = list()

        if set(current_vols_from).symmetric_difference(set(new_vols_from)):
            return True

    def compare_volumes(self, container_info):
        volumes, binds = self.generate_volumes()
        current_vols = container_info['Config'].get('Volumes')
        current_binds = container_info['HostConfig'].get('Binds')
        if not volumes:
            volumes = list()
        if not current_vols:
            current_vols = list()
        if not current_binds:
            current_binds = list()

        if set(volumes).symmetric_difference(set(current_vols)):
            return True

        new_binds = list()
        if binds:
            for k, v in binds.items():
                new_binds.append("{}:{}:{}".format(k, v['bind'], v['mode']))

        if set(new_binds).symmetric_difference(set(current_binds)):
            return True

    def compare_environment(self, container_info):
        if self.params.get('environment'):
            current_env = dict()
            for kv in container_info['Config'].get('Env', list()):
                k, v = kv.split('=', 1)
                current_env.update({k: v})

            for k, v in self.params.get('environment').items():
                if k not in current_env:
                    return True
                if current_env[k] != v:
                    return True

    def compare_container_state(self, container_info):
        new_state = self.params.get('state')
        current_state = container_info['State'].get('Status')
        if new_state != current_state:
            return True

    def compare_dimensions(self, container_info):
        new_dimensions = self.params.get('dimensions')
        # NOTE(mgoddard): The names used by Docker are inconsisent between
        # configuration of a container's resources and the resources in
        # container_info['HostConfig']. This provides a mapping between the
        # two.
        dimension_map = {
            'mem_limit': 'Memory', 'mem_reservation': 'MemoryReservation',
            'memswap_limit': 'MemorySwap', 'cpu_period': 'CpuPeriod',
            'cpu_quota': 'CpuQuota', 'cpu_shares': 'CpuShares',
            'cpuset_cpus': 'CpusetCpus', 'cpuset_mems': 'CpusetMems',
            'kernel_memory': 'KernelMemory', 'blkio_weight': 'BlkioWeight'}
        unsupported = set(new_dimensions.keys()) - \
            set(dimension_map.keys())
        if unsupported:
            self.module.exit_json(
                failed=True, msg=repr("Unsupported dimensions"),
                unsupported_dimensions=unsupported)
        current_dimensions = container_info['HostConfig']
        for key1, key2 in dimension_map.items():
            # NOTE(mgoddard): If a resource has been explicitly requested,
            # check for a match. Otherwise, ensure is is set to the default.
            if key1 in new_dimensions:
                if new_dimensions[key1] != current_dimensions[key2]:
                    return True
            elif current_dimensions[key2]:
                # The default values of all currently supported resources are
                # '' or 0 - both falsey.
                return True

    def parse_image(self):
        full_image = self.params.get('image')

        if '/' in full_image:
            registry, image = full_image.split('/', 1)
        else:
            image = full_image

        if ':' in image:
            return full_image.rsplit(':', 1)
        else:
            return full_image, 'latest'

    def get_image_id(self):
        full_image = self.params.get('image')

        image = self.dc.images(name=full_image, quiet=True)
        return image[0] if len(image) == 1 else None

    def pull_image(self):
        if self.params.get('auth_username'):
            self.dc.login(
                username=self.params.get('auth_username'),
                password=self.params.get('auth_password'),
                registry=self.params.get('auth_registry'),
                email=self.params.get('auth_email')
            )

        image, tag = self.parse_image()
        old_image_id = self.get_image_id()

        statuses = [
            json.loads(line.strip().decode('utf-8')) for line in self.dc.pull(
                repository=image, tag=tag, stream=True
            )
        ]

        for status in reversed(statuses):
            if 'error' in status:
                if status['error'].endswith('not found'):
                    self.module.fail_json(
                        msg="The requested image does not exist: {}:{}".format(
                            image, tag),
                        failed=True
                    )
                else:
                    self.module.fail_json(
                        msg="Unknown error message: {}".format(
                            status['error']),
                        failed=True
                    )

        new_image_id = self.get_image_id()
        self.changed = old_image_id != new_image_id

    def remove_container(self):
        if self.check_container():
            self.changed = True
            # NOTE(jeffrey4l): in some case, docker failed to remove container
            # filesystem and raise error.  But the container info is
            # disappeared already. If this happens, assume the container is
            # removed.
            try:
                self.dc.remove_container(
                    container=self.params.get('name'),
                    force=True
                )
            except docker.errors.APIError:
                if self.check_container():
                    raise

    def generate_volumes(self):
        volumes = self.params.get('volumes')
        if not volumes:
            return None, None

        vol_list = list()
        vol_dict = dict()

        for vol in volumes:
            if len(vol) == 0:
                continue

            if ':' not in vol:
                vol_list.append(vol)
                continue

            split_vol = vol.split(':')

            if (len(split_vol) == 2
               and ('/' not in split_vol[0] or '/' in split_vol[1])):
                split_vol.append('rw')

            vol_list.append(split_vol[1])
            vol_dict.update({
                split_vol[0]: {
                    'bind': split_vol[1],
                    'mode': split_vol[2]
                }
            })

        return vol_list, vol_dict

    def build_host_config(self, binds):
        options = {
            'network_mode': 'host',
            'ipc_mode': self.params.get('ipc_mode'),
            'cap_add': self.params.get('cap_add'),
            'security_opt': self.params.get('security_opt'),
            'pid_mode': self.params.get('pid_mode'),
            'privileged': self.params.get('privileged'),
            'volumes_from': self.params.get('volumes_from')
        }

        if self.params.get('dimensions'):
            supported = {'cpu_period', 'cpu_quota', 'cpu_shares',
                         'cpuset_cpus', 'cpuset_mems', 'mem_limit',
                         'mem_reservation', 'memswap_limit',
                         'kernel_memory', 'blkio_weight'}
            unsupported = set(self.params.get('dimensions')) - supported
            if unsupported:
                self.module.exit_json(failed=True,
                                      msg=repr("Unsupported dimensions"),
                                      unsupported_dimensions=unsupported)
            options.update(self.params.get('dimensions'))

        if self.params.get('restart_policy') in ['on-failure',
                                                 'always',
                                                 'unless-stopped']:
            policy = {'Name': self.params.get('restart_policy')}
            # NOTE(Jeffrey4l): MaximumRetryCount is only needed for on-failure
            # policy
            if self.params.get('restart_policy') == 'on-failure':
                retries = self.params.get('restart_retries')
                policy['MaximumRetryCount'] = retries
            options['restart_policy'] = policy

        if binds:
            options['binds'] = binds

        return self.dc.create_host_config(**options)

    def _inject_env_var(self, environment_info):
        newenv = {
            'KOLLA_SERVICE_NAME': self.params.get('name').replace('_', '-')
        }
        environment_info.update(newenv)
        return environment_info

    def _format_env_vars(self):
        env = self._inject_env_var(self.params.get('environment'))
        return {k: "" if env[k] is None else env[k] for k in env}

    def build_container_options(self):
        volumes, binds = self.generate_volumes()
        return {
            'detach': self.params.get('detach'),
            'environment': self._format_env_vars(),
            'host_config': self.build_host_config(binds),
            'labels': self.params.get('labels'),
            'image': self.params.get('image'),
            'name': self.params.get('name'),
            'volumes': volumes,
            'tty': True
        }

    def create_container(self):
        self.changed = True
        options = self.build_container_options()
        self.dc.create_container(**options)

    def recreate_or_restart_container(self):
        self.changed = True
        container = self.check_container()
        # get config_strategy from env
        environment = self.params.get('environment')
        config_strategy = environment.get('KOLLA_CONFIG_STRATEGY')

        if not container:
            self.start_container()
            return
        # If config_strategy is COPY_ONCE or container's parameters are
        # changed, try to start a new one.
        if config_strategy == 'COPY_ONCE' or self.check_container_differs():
            self.stop_container()
            self.remove_container()
            self.start_container()
        elif config_strategy == 'COPY_ALWAYS':
            self.restart_container()

    def start_container(self):
        if not self.check_image():
            self.pull_image()

        container = self.check_container()
        if container and self.check_container_differs():
            self.stop_container()
            self.remove_container()
            container = self.check_container()

        if not container:
            self.create_container()
            container = self.check_container()

        if not container['Status'].startswith('Up '):
            self.changed = True
            self.dc.start(container=self.params.get('name'))

        # We do not want to detach so we wait around for container to exit
        if not self.params.get('detach'):
            rc = self.dc.wait(self.params.get('name'))
            # NOTE(jeffrey4l): since python docker package 3.0, wait return a
            # dict all the time.
            if isinstance(rc, dict):
                rc = rc['StatusCode']
            if rc != 0:
                self.module.fail_json(
                    failed=True,
                    changed=True,
                    msg="Container exited with non-zero return code %s" % rc
                )
            if self.params.get('remove_on_exit'):
                self.stop_container()
                self.remove_container()

    def get_container_env(self):
        name = self.params.get('name')
        info = self.get_container_info()
        if not info:
            self.module.fail_json(msg="No such container: {}".format(name))
        else:
            envs = dict()
            for env in info['Config']['Env']:
                if '=' in env:
                    key, value = env.split('=', 1)
                else:
                    key, value = env, ''
                envs[key] = value

            self.module.exit_json(**envs)

    def get_container_state(self):
        name = self.params.get('name')
        info = self.get_container_info()
        if not info:
            self.module.fail_json(msg="No such container: {}".format(name))
        else:
            self.module.exit_json(**info['State'])

    def stop_container(self):
        name = self.params.get('name')
        graceful_timeout = self.params.get('graceful_timeout')
        if not graceful_timeout:
            graceful_timeout = 10
        container = self.check_container()
        if not container:
            self.module.fail_json(
                msg="No such container: {} to stop".format(name))
        elif not container['Status'].startswith('Exited '):
            self.changed = True
            self.dc.stop(name, timeout=graceful_timeout)

    def restart_container(self):
        name = self.params.get('name')
        graceful_timeout = self.params.get('graceful_timeout')
        if not graceful_timeout:
            graceful_timeout = 10
        info = self.get_container_info()
        if not info:
            self.module.fail_json(
                msg="No such container: {}".format(name))
        else:
            self.changed = True
            self.dc.stop(name, timeout=graceful_timeout)
            self.dc.start(name)

    def create_volume(self):
        if not self.check_volume():
            self.changed = True
            self.dc.create_volume(name=self.params.get('name'), driver='local')

    def remove_volume(self):
        if self.check_volume():
            self.changed = True
            try:
                self.dc.remove_volume(name=self.params.get('name'))
            except docker.errors.APIError as e:
                if e.response.status_code == 409:
                    self.module.fail_json(
                        failed=True,
                        msg="Volume named '{}' is currently in-use".format(
                            self.params.get('name')
                        )
                    )
                raise


def generate_module():
    # NOTE(jeffrey4l): add empty string '' to choices let us use
    # pid_mode: "{{ service.pid_mode | default ('') }}" in yaml
    argument_spec = dict(
        common_options=dict(required=False, type='dict', default=dict()),
        action=dict(required=True, type='str',
                    choices=['compare_container', 'compare_image',
                             'create_volume', 'get_container_env',
                             'get_container_state', 'pull_image',
                             'recreate_or_restart_container',
                             'remove_container', 'remove_volume',
                             'restart_container', 'start_container',
                             'stop_container']),
        api_version=dict(required=False, type='str', default='auto'),
        auth_email=dict(required=False, type='str'),
        auth_password=dict(required=False, type='str', no_log=True),
        auth_registry=dict(required=False, type='str'),
        auth_username=dict(required=False, type='str'),
        detach=dict(required=False, type='bool', default=True),
        labels=dict(required=False, type='dict', default=dict()),
        name=dict(required=False, type='str'),
        environment=dict(required=False, type='dict'),
        image=dict(required=False, type='str'),
        ipc_mode=dict(required=False, type='str', choices=['',
                                                           'host',
                                                           'private',
                                                           'shareable']),
        cap_add=dict(required=False, type='list', default=list()),
        security_opt=dict(required=False, type='list', default=list()),
        pid_mode=dict(required=False, type='str', choices=['host', '']),
        privileged=dict(required=False, type='bool', default=False),
        graceful_timeout=dict(required=False, type='int', default=10),
        remove_on_exit=dict(required=False, type='bool', default=True),
        restart_policy=dict(required=False, type='str', choices=[
                            'no',
                            'never',
                            'on-failure',
                            'always',
                            'unless-stopped']),
        restart_retries=dict(required=False, type='int', default=10),
        state=dict(required=False, type='str', default='running',
                   choices=['running',
                            'exited',
                            'paused']),
        tls_verify=dict(required=False, type='bool', default=False),
        tls_cert=dict(required=False, type='str'),
        tls_key=dict(required=False, type='str'),
        tls_cacert=dict(required=False, type='str'),
        volumes=dict(required=False, type='list'),
        volumes_from=dict(required=False, type='list'),
        dimensions=dict(required=False, type='dict', default=dict())
    )
    required_if = [
        ['action', 'pull_image', ['image']],
        ['action', 'start_container', ['image', 'name']],
        ['action', 'compare_container', ['name']],
        ['action', 'compare_image', ['name']],
        ['action', 'create_volume', ['name']],
        ['action', 'get_container_env', ['name']],
        ['action', 'get_container_state', ['name']],
        ['action', 'recreate_or_restart_container', ['name']],
        ['action', 'remove_container', ['name']],
        ['action', 'remove_volume', ['name']],
        ['action', 'restart_container', ['name']],
        ['action', 'stop_container', ['name']]
    ]
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=required_if,
        bypass_checks=False
    )

    new_args = module.params.pop('common_options', dict())

    # NOTE(jeffrey4l): merge the environment
    env = module.params.pop('environment', dict())
    if env:
        new_args['environment'].update(env)

    for key, value in module.params.items():
        if key in new_args and value is None:
            continue
        new_args[key] = value

    # if pid_mode = ""/None/False, remove it
    if not new_args.get('pid_mode', False):
        new_args.pop('pid_mode', None)
    # if ipc_mode = ""/None/False, remove it
    if not new_args.get('ipc_mode', False):
        new_args.pop('ipc_mode', None)

    module.params = new_args
    return module


def main():
    module = generate_module()

    try:
        dw = DockerWorker(module)
        # TODO(inc0): We keep it bool to have ansible deal with consistent
        # types. If we ever add method that will have to return some
        # meaningful data, we need to refactor all methods to return dicts.
        result = bool(getattr(dw, module.params.get('action'))())
        module.exit_json(changed=dw.changed, result=result)
    except Exception:
        module.exit_json(failed=True, changed=True,
                         msg=repr(traceback.format_exc()))

# import module snippets
from ansible.module_utils.basic import *  # noqa
if __name__ == '__main__':
    main()
