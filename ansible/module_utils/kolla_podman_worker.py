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

from podman.errors import APIError
from podman import PodmanClient

import shlex

from ansible.module_utils.kolla_container_worker import COMPARE_CONFIG_CMD
from ansible.module_utils.kolla_container_worker import ContainerWorker

uri = "http+unix:/run/podman/podman.sock"

CONTAINER_PARAMS = [
    'name',             # string
    'cap_add',          # list
    'cgroupns',         # 'str',choices=['private', 'host']
    'command',          # array of strings  -- docker string

    # this part is hidden inside dimensions
    'cpu_period',       # int
    'cpu_quota',        # int
    'cpuset_cpus',      # str
    'cpu_shares',       # int
    'cpuset_mems',      # str
    'kernel_memory',    # int or string
    'mem_limit',        # (Union[int, str])
    'mem_reservation',  # (Union[int, str]): Memory soft limit.
    'memswap_limit',    # (Union[int, str]): Maximum amount of memory
                        # + swap a container is allowed to consume.
    'ulimits',          # List[Ulimit]
    'blkio_weight',     # int between 10 and 1000


    'detach',           # bool
    'entrypoint',       # string
    'environment',      # dict docker - environment - dictionary
    'healthcheck',      # same schema as docker -- healthcheck
    'image',            # string
    'ipc_mode',         # string only option is host

    'labels',           # dict
    'netns',            # dict
    'network_options',  # string - none,bridge,host,container:id,
                        # missing in docker but needs to be host
    'pid_mode',         # "string"  host, private or ''
    'privileged',       # bool
    'restart_policy',   # set to none, handled by systemd
    'remove',           # bool
    'restart_tries',    # int doesn't matter done by systemd
    'stop_timeout',     # int
    'tty',              # bool
    # volumes need to be parsed, see parse_volumes() for more info
    'volumes',          # array of dict
    'volumes_from',     # array of strings
]


class PodmanWorker(ContainerWorker):

    def __init__(self, module) -> None:
        super().__init__(module)

        self.pc = PodmanClient(base_url=uri)

    def prepare_container_args(self):
        args = dict(
            network_mode='host'
        )

        command = self.params.pop('command', '')
        if command:
            self.params['command'] = shlex.split(command)

        #  we have to transform volumes into mounts because podman-py
        #  functionality is broken
        mounts = []
        filtered_volumes = {}
        volumes = self.params.get('volumes')
        if volumes:
            self.parse_volumes(volumes, mounts, filtered_volumes)
            # we can delete original volumes so it won't raise error later
            self.params.pop('volumes', None)

        args['mounts'] = mounts
        args['volumes'] = filtered_volumes

        env = self._format_env_vars()
        args['environment'] = {k: str(v) for k, v in env.items()}
        self.params.pop('environment', None)

        healthcheck = self.params.get('healthcheck')
        if healthcheck:
            healthcheck = self.parse_healthcheck(healthcheck)
            self.params.pop('healthcheck', None)
            if healthcheck:
                args.update(healthcheck)

        # getting dimensions into separate parameters
        dimensions = self.params.get('dimensions')
        if dimensions:
            dimensions = self.parse_dimensions(dimensions)
            args.update(dimensions)

        # NOTE(m.hiner): currently unsupported by Podman API
        # args['tmpfs'] = self.generate_tmpfs()
        self.params.pop('tmpfs', None)

        # NOTE(m.hiner): in case containers are not privileged,
        # they need this capability
        if not self.params.get('privileged', False):
            args['cap_add'] = self.params.pop('cap_add', []) + ['AUDIT_WRITE']

        # maybe can be done straight away,
        # at first it was around 6 keys that's why it is this way
        convert_keys = dict(
            graceful_timeout='stop_timeout',
            cgroupns_mode='cgroupns'
        )

        # remap differing args
        for key_orig, key_new in convert_keys.items():
            if key_orig in self.params:
                value = self.params.get(key_orig, None)

                if value is not None:
                    args[key_new] = value

        # record remaining args
        for key, value in self.params.items():
            if key in CONTAINER_PARAMS and value is not None:
                args[key] = value

        args.pop('restart_policy', None)    # handled by systemd

        return args

    # NOTE(i.halomi): Podman encounters issues parsing and setting
    # permissions for a mix of volumes and binds when sent together.
    # Therefore, we must parse them and set the permissions ourselves
    # and send them to API separately.
    def parse_volumes(self, volumes, mounts, filtered_volumes):
        for item in volumes:
            if not item or not item.strip():
                # we can ignore empty strings or null volumes
                continue
            # if it starts with / it is bind not volume
            if item[0] == '/':
                mode = None
                try:
                    if item.count(':') == 2:
                        src, dest, mode = item.split(':')
                    else:
                        src, dest = item.split(':')
                except ValueError:
                    self.module.fail_json(
                        msg="Wrong format of volume: {}".format(item),
                        failed=True
                    )

                mount_item = dict(
                    source=src,
                    target=dest,
                    type='bind',
                    propagation='rprivate'
                )
                if mode == 'ro':
                    mount_item['read_only'] = True
                if mode == 'shared':
                    mount_item['propagation'] = 'shared'
                mounts.append(mount_item)
            else:
                try:
                    mode = 'rw'
                    if item.count(':') == 2:
                        src, dest, mode = item.split(':')
                    else:
                        src, dest = item.split(':')
                except ValueError:
                    self.module.fail_json(
                        msg="Wrong format of volume: {}".format(item),
                        failed=True
                    )
                if src == 'devpts':
                    mount_item = dict(
                        target=dest,
                        type='devpts'
                    )
                    mounts.append(mount_item)
                else:
                    filtered_volumes[src] = dict(
                        bind=dest,
                        mode=mode
                    )

    def parse_dimensions(self, dimensions):
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

        ulimits = dimensions.get('ulimits', {})
        if ulimits:
            # NOTE(m.hiner): default ulimits have to be filtered out because
            # Podman would treat them as new ulimits and break the container
            # as a result. Names are a copy of
            # default_podman_dimensions_el9 in group_vars
            for name in ['RLIMIT_NOFILE', 'RLIMIT_NPROC']:
                ulimits.pop(name, None)

            dimensions['ulimits'] = self.build_ulimits(ulimits)

        return dimensions

    def parse_healthcheck(self, healthcheck):
        hc = super().parse_healthcheck(healthcheck)

        # rename key to right format
        if hc:
            sp = hc['healthcheck'].pop('start_period', None)
            if sp:
                hc['healthcheck']['StartPeriod'] = sp

        return hc

    def prepare_image_args(self):
        image, tag = self.parse_image()

        args = dict(
            repository=image,
            tag=tag,
            tls_verify=self.params.get('tls_verify', False),
            stream=False
        )

        if self.params.get('auth_username', False):
            args['auth_config'] = dict(
                username=self.params.get('auth_username'),
                password=self.params.get('auth_password', "")
            )

        if '/' not in image and self.params.get('auth_registry', False):
            args['image'] = self.params['auth_registry'] + '/' + image
        return args

    def check_image(self):
        try:
            image = self.pc.images.get(self.params.get('image'))
            return image.attrs
        except APIError as e:
            if e.status_code == 404:
                return {}
            else:
                self.module.fail_json(
                    failed=True,
                    msg="Internal error: {}".format(
                        e.explanation
                    )
                )

    def check_volume(self, name=None):
        volume_name = name if name else self.params.get('name')
        try:
            vol = self.pc.volumes.get(volume_name)
            return vol.attrs
        except APIError as e:
            if e.status_code == 404:
                return {}

    def check_container(self):
        name = self.params.get("name")
        for cont in self.pc.containers.list(all=True):
            cont.reload()
            if name == cont.name:
                return cont

    def get_container_info(self):
        container = self.check_container()
        if not container:
            return None

        return container.attrs

    def compare_container(self):
        container = self.check_container()
        if (not container or
                self.check_container_differs() or
                self.compare_config() or
                self.systemd.check_unit_change()):
            self.changed = True
        return self.changed

    def compare_pid_mode(self, container_info):
        new_pid_mode = self.params.get('pid_mode') or self.params.get('pid')
        current_pid_mode = container_info['HostConfig'].get('PidMode')

        if not current_pid_mode:
            current_pid_mode = None

        # podman default pid_mode
        if new_pid_mode is None and current_pid_mode == 'private':
            return False

        if new_pid_mode != current_pid_mode:
            return True

    def compare_image(self, container_info=None):
        def parse_tag(tag):
            splits = tag.rsplit('/', 1)
            return splits[-1]

        container_info = container_info or self.get_container_info()
        if not container_info:
            return True

        new_image = self.check_image()
        current_image = container_info['Image']
        if not new_image:
            return True
        if new_image['Id'] != current_image:
            return True
        # compare name:tag
        elif (parse_tag(self.params.get('image')) !=
              parse_tag(container_info['Config']['Image'])):
            return True

    def compare_volumes(self, container_info):
        def check_slash(string):
            if not string:
                return string
            if string[-1] != '/':
                return string + '/'
            else:
                return string

        raw_volumes, binds = self.generate_volumes()
        raw_vols, current_binds = self.generate_volumes(
            container_info['HostConfig'].get('Binds'))

        current_vols = [check_slash(vol) for vol in raw_vols if vol]
        volumes = [check_slash(vol) for vol in raw_volumes if vol]

        if not volumes:
            volumes = list()
        if not current_vols:
            current_vols = list()
        if not current_binds:
            current_binds = list()

        volumes.sort()
        current_vols.sort()

        if set(volumes).symmetric_difference(set(current_vols)):
            return True

        new_binds = list()
        new_current_binds = list()
        if binds:
            for k, v in binds.items():
                k = check_slash(k)
                v['bind'] = check_slash(v['bind'])
                new_binds.append(
                    "{}:{}:{}".format(k, v['bind'], v['mode']))

        if current_binds:
            for k, v in current_binds.items():
                k = check_slash(k)
                v['bind'] = check_slash(v['bind'])
                if 'ro' in v['mode']:
                    v['mode'] = 'ro'
                else:
                    v['mode'] = 'rw'
                new_current_binds.append(
                    "{}:{}:{}".format(k, v['bind'], v['mode'][0:2]))

        new_binds.sort()
        new_current_binds.sort()

        if set(new_binds).symmetric_difference(set(new_current_binds)):
            return True

    def compare_dimensions(self, container_info):
        new_dimensions = self.params.get('dimensions')

        # NOTE(mgoddard): The names used by Docker/Podman are inconsistent
        # between configuration of a container's resources and
        # the resources in container_info['HostConfig'].
        # This provides a mapping between the two.
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
                # The default values of all (except ulimits) currently
                # supported resources are '' or 0 - both falsey.
                return True

    def compare_config(self):
        try:
            container = self.pc.containers.get(self.params['name'])
            container.reload()
            if container.status != 'running':
                return True

            rc, raw_output = container.exec_run(COMPARE_CONFIG_CMD,
                                                user='root')
        # APIError means either container doesn't exist or exec command
        # failed, which means that container is in bad state and we can
        # expect that config is stale so we return True and recreate container
        except APIError as e:
            if e.is_client_error():
                return True
            else:
                raise
        # Exit codes:
        # 0: not changed
        # 1: changed
        # else: error
        if rc == 0:
            return False
        elif rc == 1:
            return True
        else:
            raise Exception('Failed to compare container configuration: '
                            'ExitCode: %s Message: %s' %
                            (rc, raw_output.decode('utf-8')))

    def pull_image(self):
        args = self.prepare_image_args()
        old_image = self.check_image()

        try:
            image = self.pc.images.pull(**args)

            if image.attrs == {}:
                self.module.fail_json(
                    msg="The requested image does not exist: {}".format(
                        self.params['image']),
                    failed=True
                )
            self.changed = old_image != image.attrs
        except APIError as e:
            self.module.fail_json(
                msg="Unknown error message: {}".format(
                    str(e)),
                failed=True
            )

    def remove_container(self):
        self.changed |= self.systemd.remove_unit_file()
        container = self.check_container()
        if container:
            try:
                container.remove(force=True)
            except APIError:
                if self.check_container():
                    raise

    def build_ulimits(self, ulimits):
        ulimits_opt = []
        for key, value in ulimits.items():
            soft = value.get('soft')
            hard = value.get('hard')
            # Converted to simple dictionary instead of Ulimit type
            ulimits_opt.append(dict(Name=key,
                                    Soft=soft,
                                    Hard=hard))
        return ulimits_opt

    def create_container(self):
        # ensure volumes are pre-created before container creation
        self.create_container_volumes()

        args = self.prepare_container_args()
        container = self.pc.containers.create(**args)
        if container.attrs == {}:
            data = container.to_dict()
            self.module.fail_json(failed=True, msg="Creation failed", **data)
        else:
            self.changed |= self.systemd.create_unit_file()
        return container

    def recreate_or_restart_container(self):
        strategy = self.params.get(
            'environment', dict()).get('KOLLA_CONFIG_STRATEGY')

        container = self.get_container_info()
        if not container:
            self.start_container()
            return

        if strategy == 'COPY_ONCE' or self.check_container_differs():
            self.ensure_image()

            self.stop_container()
            self.remove_container()
            self.start_container()

        elif strategy == 'COPY_ALWAYS':
            self.restart_container()

    def start_container(self):
        self.ensure_image()

        container = self.check_container()
        if container and self.check_container_differs():
            self.stop_container()
            self.remove_container()
            container = self.check_container()

        if not container:
            self.create_container()
            container = self.check_container()

        if container.status != 'running':
            self.changed = True
            if self.params.get('restart_policy') == 'oneshot':
                container = self.check_container()
                container.start()
            else:
                self.systemd.create_unit_file()
                if not self.systemd.start():
                    self.module.fail_json(
                        changed=True,
                        msg="Container timed out",
                        **self.check_container().attrs)

        if not self.params.get('detach'):
            container = self.check_container()
            rc = container.wait()

            stdout = [line.decode() for line in container.logs(stdout=True,
                      stderr=False)]
            stderr = [line.decode() for line in container.logs(stdout=False,
                      stderr=True)]

            self.result['rc'] = rc
            self.result['stdout'] = "\n".join(stdout) if len(stdout) else ""
            self.result['stderr'] = "\n".join(stderr) if len(stderr) else ""

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
        elif not (container.status == 'exited' or
                  container.status == 'stopped'):
            self.changed = True
            if self.params.get('restart_policy') != 'oneshot':
                self.systemd.create_unit_file()
                self.systemd.stop()
            else:
                container.stop(timeout=str(graceful_timeout))

    def stop_and_remove_container(self):
        container = self.check_container()

        if container:
            self.stop_container()
            self.remove_container()

    def restart_container(self):
        container = self.check_container()

        if not container:
            self.module.fail_json(
                msg="No such container: {}".format(self.params.get('name'))
            )
        else:
            self.changed = True
            self.systemd.create_unit_file()

            if not self.systemd.restart():
                self.module.fail_json(
                    changed=True,
                    msg="Container timed out",
                    **container.attrs)

    def create_volume(self, name=None):
        volume_name = name if name else self.params.get('name')
        if not self.check_volume(name=volume_name):
            self.changed = True
            args = dict(
                name=volume_name,
                driver='local',
                labels={'kolla_managed': 'true'}
            )

            vol = self.pc.volumes.create(**args)
            self.result = vol.attrs

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
                self.pc.volumes.remove(self.params.get('name'))
            except APIError as e:
                if e.status_code == 409:
                    self.module.fail_json(
                        failed=True,
                        msg="Volume named '{}' is currently in-use".format(
                            self.params.get('name')
                        )
                    )
                else:
                    self.module.fail_json(
                        failed=True,
                        msg="Internal error: {}".format(
                            e.explanation
                        )
                    )
                raise

    def remove_image(self):
        if self.check_image():
            image = self.pc.images.get(self.params['image'])
            self.changed = True
            try:
                image.remove()
            except APIError as e:
                if e.status_code == 409:
                    self.module.fail_json(
                        failed=True,
                        msg="Image '{}' is currently in-use".format(
                            self.params.get('image')
                        )
                    )
                else:
                    self.module.fail_json(
                        failed=True,
                        msg="Internal error: {}".format(
                            str(e)
                        )
                    )
                raise

    def ensure_image(self):
        if not self.check_image():
            self.pull_image()
