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

import docker
import json
import os

from ansible.module_utils.kolla_container_worker import COMPARE_CONFIG_CMD
from ansible.module_utils.kolla_container_worker import ContainerWorker


def get_docker_client():
    return docker.APIClient


class DockerWorker(ContainerWorker):

    def __init__(self, module):
        super().__init__(module)

        options = {
            'version': self.params.get('api_version'),
            'timeout': self.params.get('client_timeout'),
        }

        self.dc = get_docker_client()(**options)

        self._dimensions_kernel_memory_removed = True
        self.dimension_map.pop('kernel_memory', None)

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

    def compare_pid_mode(self, container_info):
        new_pid_mode = self.params.get('pid_mode')
        current_pid_mode = container_info['HostConfig'].get('PidMode')
        if not current_pid_mode:
            current_pid_mode = None

        if new_pid_mode != current_pid_mode:
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
        self.changed |= self.systemd.remove_unit_file()
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
                self.systemd.remove_unit_file()
            except docker.errors.APIError:
                if self.check_container():
                    raise

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

        if binds:
            options['binds'] = binds

        host_config = self.dc.create_host_config(**options)

        # NOTE(yoctozepto): python-docker does not support CgroupnsMode
        # natively so we stuff it in manually.
        cgroupns_mode = self.params.get('cgroupns_mode')
        if cgroupns_mode is not None:
            host_config['CgroupnsMode'] = cgroupns_mode

        # detached containers should only log to journald
        if self.params.get('detach'):
            options['log_config'] = docker.types.LogConfig(
                type=docker.types.LogConfig.types.NONE)

        return host_config

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
        # ensure volumes are pre-created before container creation
        self.create_container_volumes()

        options = self.build_container_options()
        self.dc.create_container(**options)
        if self.params.get('restart_policy') != 'oneshot':
            self.changed |= self.systemd.create_unit_file()

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
            if self.params.get('restart_policy') == 'oneshot':
                self.dc.start(container=self.params.get('name'))
            else:
                self.systemd.create_unit_file()
                if not self.systemd.start():
                    self.module.fail_json(
                        changed=True,
                        msg="Container timed out",
                        **self.check_container())

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
            if not self.systemd.check_unit_file():
                self.dc.stop(name, timeout=graceful_timeout)
            else:
                self.systemd.stop()

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
            if self.params.get('restart_policy') != 'oneshot':
                self.systemd.create_unit_file()
                if not self.systemd.restart():
                    self.module.fail_json(
                        changed=True,
                        msg="Container timed out",
                        **self.check_container())
            else:
                self.dc.stop(name, timeout=graceful_timeout)
                self.dc.start(name)

    def create_volume(self, name=None):
        volume_name = name if name else self.params.get('name')
        if not self.check_volume():
            self.changed = True
            self.dc.create_volume(name=volume_name, driver='local',
                                  labels={'kolla_managed': 'true'})

    def create_container_volumes(self):
        volumes = self.params.get('volumes')
        if not volumes:
            return
        # Filter out null / empty string volumes
        volumes = [v for v in volumes if v]
        for volume in volumes:
            volume_name = volume.split(":")[0]
            if "/" in volume_name:
                continue

            self.create_volume(name=volume_name)

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
