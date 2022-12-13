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

# FIXME(yoctozepto): restart_policy is *not* checked in the container

import docker
import json
import os
import shlex

from distutils.version import StrictVersion

COMPARE_CONFIG_CMD = ['/usr/local/bin/kolla_set_configs', '--check']


def get_docker_client():
    return docker.APIClient


class DockerWorker(object):

    def __init__(self, module):
        self.module = module
        self.params = self.module.params
        self.changed = False
        # Use this to store arguments to pass to exit_json().
        self.result = {}

        # TLS not fully implemented
        # tls_config = self.generate_tls()

        options = {
            'version': self.params.get('api_version'),
            'timeout': self.params.get('client_timeout'),
        }

        self.dc = get_docker_client()(**options)

        self._cgroupns_mode_supported = (
            StrictVersion(self.dc._version) >= StrictVersion('1.41'))

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
        if (not container or
                self.check_container_differs() or
                self.compare_config()):
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
            self.compare_cgroupns_mode(container_info) or
            self.compare_tmpfs(container_info) or
            self.compare_volumes(container_info) or
            self.compare_volumes_from(container_info) or
            self.compare_environment(container_info) or
            self.compare_container_state(container_info) or
            self.compare_dimensions(container_info) or
            self.compare_command(container_info) or
            self.compare_healthcheck(container_info)
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

    def compare_cgroupns_mode(self, container_info):
        if not self._cgroupns_mode_supported:
            return False
        new_cgroupns_mode = self.params.get('cgroupns_mode')
        if new_cgroupns_mode is None:
            # means we don't care what it is
            return False
        current_cgroupns_mode = (container_info['HostConfig']
                                 .get('CgroupnsMode'))
        if current_cgroupns_mode == '':
            # means the container was created on Docker pre-20.10
            # it behaves like 'host'
            current_cgroupns_mode = 'host'
        return new_cgroupns_mode != current_cgroupns_mode

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

    def compare_tmpfs(self, container_info):
        new_tmpfs = self.generate_tmpfs()
        current_tmpfs = container_info['HostConfig'].get('Tmpfs')
        if not new_tmpfs:
            new_tmpfs = []
        if not current_tmpfs:
            current_tmpfs = []

        if set(current_tmpfs).symmetric_difference(set(new_tmpfs)):
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
            'kernel_memory': 'KernelMemory', 'blkio_weight': 'BlkioWeight',
            'ulimits': 'Ulimits'}
        unsupported = set(new_dimensions.keys()) - \
            set(dimension_map.keys())
        if unsupported:
            self.module.exit_json(
                failed=True, msg=repr("Unsupported dimensions"),
                unsupported_dimensions=unsupported)
        current_dimensions = container_info['HostConfig']
        for key1, key2 in dimension_map.items():
            # NOTE(mgoddard): If a resource has been explicitly requested,
            # check for a match. Otherwise, ensure it is set to the default.
            if key1 in new_dimensions:
                if key1 == 'ulimits':
                    if self.compare_ulimits(new_dimensions[key1],
                                            current_dimensions[key2]):
                        return True
                elif new_dimensions[key1] != current_dimensions[key2]:
                    return True
            elif current_dimensions[key2]:
                # The default values of all currently supported resources are
                # '' or 0 - both falsey.
                return True

    def compare_ulimits(self, new_ulimits, current_ulimits):
        # The new_ulimits is dict, we need make it to a list of Ulimit
        # instance.
        new_ulimits = self.build_ulimits(new_ulimits)

        def key(ulimit):
            return ulimit['Name']

        if current_ulimits is None:
            current_ulimits = []
        return sorted(new_ulimits, key=key) != sorted(current_ulimits, key=key)

    def compare_command(self, container_info):
        new_command = self.params.get('command')
        if new_command is not None:
            new_command_split = shlex.split(new_command)
            new_path = new_command_split[0]
            new_args = new_command_split[1:]
            if (new_path != container_info['Path'] or
                    new_args != container_info['Args']):
                return True

    def compare_healthcheck(self, container_info):
        new_healthcheck = self.parse_healthcheck(
            self.params.get('healthcheck'))
        current_healthcheck = container_info['Config'].get('Healthcheck')

        healthcheck_map = {
            'test': 'Test',
            'retries': 'Retries',
            'interval': 'Interval',
            'start_period': 'StartPeriod',
            'timeout': 'Timeout'}

        if new_healthcheck:
            new_healthcheck = new_healthcheck['healthcheck']
            if current_healthcheck:
                new_healthcheck = dict((healthcheck_map.get(k, k), v)
                                       for (k, v) in new_healthcheck.items())
                return new_healthcheck != current_healthcheck
            else:
                return True
        else:
            if current_healthcheck:
                return True

    def compare_config(self):
        try:
            job = self.dc.exec_create(
                self.params['name'],
                COMPARE_CONFIG_CMD,
                user='root',
            )
            output = self.dc.exec_start(job)
            exec_inspect = self.dc.exec_inspect(job)
        except docker.errors.APIError as e:
            # NOTE(yoctozepto): If we have a client error, then the container
            # cannot be used for config check (e.g., is restarting, or stopped
            # in the mean time) - assume config is stale = return True.
            # Else, propagate the server error back.
            if e.is_client_error():
                return True
            else:
                raise
        # Exit codes:
        # 0: not changed
        # 1: changed
        # 137: abrupt exit -> changed
        # else: error
        if exec_inspect['ExitCode'] == 0:
            return False
        elif exec_inspect['ExitCode'] == 1:
            return True
        elif exec_inspect['ExitCode'] == 137:
            # NOTE(yoctozepto): This is Docker's command exit due to container
            # exit. It means the container is unstable so we are better off
            # marking it as requiring a restart due to config update.
            return True
        else:
            raise Exception('Failed to compare container configuration: '
                            'ExitCode: %s Message: %s' %
                            (exec_inspect['ExitCode'], output))

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

    def generate_tmpfs(self):
        tmpfs = self.params.get('tmpfs')
        if tmpfs:
            # NOTE(mgoddard): Filter out any empty strings.
            tmpfs = [t for t in tmpfs if t]
        return tmpfs

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

            if (len(split_vol) == 2 and
               ('/' not in split_vol[0] or '/' in split_vol[1])):
                split_vol.append('rw')

            vol_list.append(split_vol[1])
            vol_dict.update({
                split_vol[0]: {
                    'bind': split_vol[1],
                    'mode': split_vol[2]
                }
            })

        return vol_list, vol_dict

    def parse_dimensions(self, dimensions):
        # When the data object contains types such as
        # docker.types.Ulimit, Ansible will fail when these are
        # returned via exit_json or fail_json. HostConfig is derived from dict,
        # but its constructor requires additional arguments.
        # to avoid that, here do copy the dimensions and return a new one.
        dimensions = dimensions.copy()

        supported = {'cpu_period', 'cpu_quota', 'cpu_shares',
                     'cpuset_cpus', 'cpuset_mems', 'mem_limit',
                     'mem_reservation', 'memswap_limit',
                     'kernel_memory', 'blkio_weight', 'ulimits'}
        unsupported = set(dimensions) - supported
        if unsupported:
            self.module.exit_json(failed=True,
                                  msg=repr("Unsupported dimensions"),
                                  unsupported_dimensions=unsupported)

        ulimits = dimensions.get('ulimits')
        if ulimits:
            dimensions['ulimits'] = self.build_ulimits(ulimits)

        return dimensions

    def build_ulimits(self, ulimits):
        ulimits_opt = []
        for key, value in ulimits.items():
            soft = value.get('soft')
            hard = value.get('hard')
            ulimits_opt.append(docker.types.Ulimit(name=key,
                                                   soft=soft,
                                                   hard=hard))
        return ulimits_opt

    def build_host_config(self, binds):
        options = {
            'network_mode': 'host',
            'ipc_mode': self.params.get('ipc_mode'),
            'cap_add': self.params.get('cap_add'),
            'security_opt': self.params.get('security_opt'),
            'pid_mode': self.params.get('pid_mode'),
            'privileged': self.params.get('privileged'),
            'tmpfs': self.generate_tmpfs(),
            'volumes_from': self.params.get('volumes_from')
        }

        dimensions = self.params.get('dimensions')

        if dimensions:
            dimensions = self.parse_dimensions(dimensions)
            options.update(dimensions)

        restart_policy = self.params.get('restart_policy')

        if restart_policy is not None:
            restart_policy = {'Name': restart_policy}
            # NOTE(Jeffrey4l): MaximumRetryCount is only needed for on-failure
            # policy
            if restart_policy['Name'] == 'on-failure':
                retries = self.params.get('restart_retries')
                if retries is not None:
                    restart_policy['MaximumRetryCount'] = retries
            options['restart_policy'] = restart_policy

        if binds:
            options['binds'] = binds

        host_config = self.dc.create_host_config(**options)

        if self._cgroupns_mode_supported:
            # NOTE(yoctozepto): python-docker does not support CgroupnsMode
            # natively so we stuff it in manually.
            cgroupns_mode = self.params.get('cgroupns_mode')
            if cgroupns_mode is not None:
                host_config['CgroupnsMode'] = cgroupns_mode

        return host_config

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

        options = {
            'command': self.params.get('command'),
            'detach': self.params.get('detach'),
            'environment': self._format_env_vars(),
            'host_config': self.build_host_config(binds),
            'labels': self.params.get('labels'),
            'image': self.params.get('image'),
            'name': self.params.get('name'),
            'volumes': volumes,
            'tty': self.params.get('tty'),
        }

        healthcheck = self.parse_healthcheck(self.params.get('healthcheck'))
        if healthcheck:
            options.update(healthcheck)

        return options

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
            # NOTE(mgoddard): Pull the image if necessary before stopping the
            # container, otherwise a failure to pull the image will leave the
            # container stopped.
            if not self.check_image():
                self.pull_image()
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
            # Include container's return code, standard output and error in the
            # result.
            self.result['rc'] = rc
            self.result['stdout'] = self.dc.logs(self.params.get('name'),
                                                 stdout=True, stderr=False)
            self.result['stderr'] = self.dc.logs(self.params.get('name'),
                                                 stdout=False, stderr=True)
            if self.params.get('remove_on_exit'):
                self.stop_container()
                self.remove_container()
            if rc != 0:
                self.module.fail_json(
                    changed=True,
                    msg="Container exited with non-zero return code %s" % rc,
                    **self.result
                )

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

    def parse_healthcheck(self, healthcheck):
        if not healthcheck:
            return None

        result = dict(healthcheck={})

        # All supported healthcheck parameters
        supported = set(['test', 'interval', 'timeout', 'start_period',
                         'retries'])
        unsupported = set(healthcheck) - supported
        missing = supported - set(healthcheck)
        duration_options = set(['interval', 'timeout', 'start_period'])

        if unsupported:
            self.module.exit_json(failed=True,
                                  msg=repr("Unsupported healthcheck options"),
                                  unsupported_healthcheck=unsupported)

        if missing:
            self.module.exit_json(failed=True,
                                  msg=repr("Missing healthcheck option"),
                                  missing_healthcheck=missing)

        for key in healthcheck:
            value = healthcheck.get(key)
            if key in duration_options:
                try:
                    result['healthcheck'][key] = int(value) * 1000000000
                except TypeError:
                    raise TypeError(
                        'Cannot parse healthcheck "{0}". '
                        'Expected an integer, got "{1}".'
                        .format(value, type(value).__name__)
                    )
                except ValueError:
                    raise ValueError(
                        'Cannot parse healthcheck "{0}". '
                        'Expected an integer, got "{1}".'
                        .format(value, type(value).__name__)
                    )
            else:
                if key == 'test':
                    # If the user explicitly disables the healthcheck,
                    # return None as the healthcheck object
                    if value in (['NONE'], 'NONE'):
                        return None
                    else:
                        if isinstance(value, (tuple, list)):
                            result['healthcheck'][key] = \
                                [str(e) for e in value]
                        else:
                            result['healthcheck'][key] = \
                                ['CMD-SHELL', str(value)]
                elif key == 'retries':
                    try:
                        result['healthcheck'][key] = int(value)
                    except ValueError:
                        raise ValueError(
                            'Cannot parse healthcheck number of retries.'
                            'Expected an integer, got "{0}".'
                            .format(type(value))
                        )

        return result

    def stop_container(self):
        name = self.params.get('name')
        graceful_timeout = self.params.get('graceful_timeout')
        if not graceful_timeout:
            graceful_timeout = 10
        container = self.check_container()
        if not container:
            ignore_missing = self.params.get('ignore_missing')
            if not ignore_missing:
                self.module.fail_json(
                    msg="No such container: {} to stop".format(name))
        elif not container['Status'].startswith('Exited '):
            self.changed = True
            self.dc.stop(name, timeout=graceful_timeout)

    def stop_and_remove_container(self):
        container = self.check_container()
        if container:
            self.stop_container()
            self.remove_container()

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

    def remove_image(self):
        if self.check_image():
            self.changed = True
            try:
                self.dc.remove_image(image=self.params.get('image'))
            except docker.errors.APIError as e:
                if e.response.status_code == 409:
                    self.module.fail_json(
                        failed=True,
                        msg="Image '{}' is currently in-use".format(
                            self.params.get('image')
                        )
                    )
                elif e.response.status_code == 500:
                    self.module.fail_json(
                        failed=True,
                        msg="Server error"
                    )
                raise

    def ensure_image(self):
        if not self.check_image():
            self.pull_image()
