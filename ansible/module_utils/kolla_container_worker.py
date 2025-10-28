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

from abc import ABC
from abc import abstractmethod
import logging
import shlex

from ansible.module_utils.kolla_systemd_worker import SystemdWorker

COMPARE_CONFIG_CMD = ['/usr/local/bin/kolla_set_configs', '--check']
LOG = logging.getLogger(__name__)


class ContainerWorker(ABC):
    def __init__(self, module):
        self.module = module
        self.params = self.module.params
        self.changed = False
        # Use this to store arguments to pass to exit_json().
        self.result = {}

        self.systemd = SystemdWorker(self.params)

        # NOTE(mgoddard): The names used by Docker are inconsistent between
        # configuration of a container's resources and the resources in
        # container_info['HostConfig']. This provides a mapping between the
        # two.
        self.dimension_map = {
            'mem_limit': 'Memory', 'mem_reservation': 'MemoryReservation',
            'memswap_limit': 'MemorySwap', 'cpu_period': 'CpuPeriod',
            'cpu_quota': 'CpuQuota', 'cpu_shares': 'CpuShares',
            'cpuset_cpus': 'CpusetCpus', 'cpuset_mems': 'CpusetMems',
            'kernel_memory': 'KernelMemory', 'blkio_weight': 'BlkioWeight',
            'ulimits': 'Ulimits'}

    @abstractmethod
    def check_image(self):
        pass

    @abstractmethod
    def get_container_info(self):
        pass

    @abstractmethod
    def check_container(self):
        pass

    def compare_container(self):
        container = self.check_container()
        if (not container or
                self.check_container_differs() or
                self.compare_config() or
                self.systemd.check_unit_change()):
            self.changed = True
        return self.changed

    def check_container_differs(self):
        container_info = self.get_container_info()
        if not container_info:
            return True

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
        try:
            current_cap_add = container_info['HostConfig'].get('CapAdd', None)
        except KeyError:
            current_cap_add = None
        except TypeError:
            current_cap_add = None

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
        try:
            current_sec_opt = container_info['HostConfig'].get('SecurityOpt',
                                                               list())
        except KeyError:
            current_sec_opt = None
        except TypeError:
            current_sec_opt = None

        if not current_sec_opt:
            current_sec_opt = list()
        if set(new_sec_opt).symmetric_difference(set(current_sec_opt)):
            return True

    @abstractmethod
    def compare_pid_mode(self, container_info):
        pass

    def compare_cgroupns_mode(self, container_info):
        new_cgroupns_mode = self.params.get('cgroupns_mode')
        if new_cgroupns_mode is None:
            # means we don't care what it is
            return False
        current_cgroupns_mode = (container_info['HostConfig']
                                 .get('CgroupnsMode')) or \
                                (container_info['HostConfig']
                                 .get('CgroupMode'))
        if current_cgroupns_mode in ('', None):
            # means the container was created on Docker pre-20.10
            # it behaves like 'host'
            current_cgroupns_mode = 'host'
        return new_cgroupns_mode != current_cgroupns_mode

    def compare_privileged(self, container_info):
        new_privileged = self.params.get('privileged')
        current_privileged = container_info['HostConfig']['Privileged']
        if new_privileged != current_privileged:
            return True

    @abstractmethod
    def compare_image(self, container_info=None):
        pass

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

    @abstractmethod
    def compare_volumes(self, container_info):
        pass

    def dimensions_differ(self, a, b, key):
        """Compares two docker dimensions

        As there are two representations of dimensions in docker, we should
        normalize them to compare if they are the same.

        If the dimension is no more supported due docker update,
        an error is thrown to operator to fix the dimensions' config.

        The available representations can be found at:

        https://docs.docker.com/config/containers/resource_constraints/


        :param a: Integer or String that represents a number followed or not
                  by "b", "k", "m" or "g".
        :param b: Integer or String that represents a number followed or not
                  by "b", "k", "m" or "g".
        :return: True if 'a' has the same logical value as 'b' or else
                 False.
        """

        if a is None or b is None:
            msg = ("The dimension [%s] is no more supported by Docker, "
                   "please remove it from yours configs or change "
                   "to the new one.") % key
            LOG.error(msg)
            self.module.fail_json(
                failed=True,
                msg=msg
            )
            return

        unit_sizes = {
            'b': 1,
            'k': 1024
        }
        unit_sizes['m'] = unit_sizes['k'] * 1024
        unit_sizes['g'] = unit_sizes['m'] * 1024
        a = str(a)
        b = str(b)
        a_last_char = a[-1].lower()
        b_last_char = b[-1].lower()
        error_msg = ("The docker dimension unit [%s] is not supported for "
                     "the dimension [%s]. The currently supported units "
                     "are ['b', 'k', 'm', 'g'].")
        if not a_last_char.isnumeric():
            if a_last_char in unit_sizes:
                a = str(int(a[:-1]) * unit_sizes[a_last_char])
            else:
                LOG.error(error_msg, a_last_char, a)
                self.module.fail_json(
                    failed=True,
                    msg=error_msg % (a_last_char, a)
                )

        if not b_last_char.isnumeric():
            if b_last_char in unit_sizes:
                b = str(int(b[:-1]) * unit_sizes[b_last_char])
            else:
                LOG.error(error_msg, b_last_char, b)
                self.module.fail_json(
                    failed=True,
                    msg=error_msg % (b_last_char, b)
                )
        return a != b

    def compare_dimensions(self, container_info):
        new_dimensions = self.params.get('dimensions')

        if not self._dimensions_kernel_memory_removed:
            self.dimension_map['kernel_memory'] = 'KernelMemory'

        unsupported = set(new_dimensions.keys()) - \
            set(self.dimension_map.keys())
        if unsupported:
            self.module.exit_json(
                failed=True, msg=repr("Unsupported dimensions"),
                unsupported_dimensions=unsupported)
        current_dimensions = container_info['HostConfig']
        for key1, key2 in self.dimension_map.items():
            # NOTE(mgoddard): If a resource has been explicitly requested,
            # check for a match. Otherwise, ensure it is set to the default.
            if key1 in new_dimensions:
                if key1 == 'ulimits':
                    if self.compare_ulimits(new_dimensions.get(key1),
                                            current_dimensions.get(key2)):
                        return True
                elif self.dimensions_differ(new_dimensions.get(key1),
                                            current_dimensions.get(key2),
                                            key1):
                    return True
            elif current_dimensions.get(key2):
                # The default values of all currently supported resources are
                # '' or 0 - both falsy.
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

        if new_state == "started" and current_state == "running":
            return False
        if new_state != current_state:
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

    @abstractmethod
    def pull_image(self):
        pass

    @abstractmethod
    def remove_container(self):
        pass

    def generate_tmpfs(self):
        tmpfs = self.params.get('tmpfs')
        if tmpfs:
            # NOTE(mgoddard): Filter out any empty strings.
            tmpfs = [t for t in tmpfs if t]
        return tmpfs

    def generate_volumes(self, binds=None):
        if not binds:
            volumes = self.params.get('volumes') or self.params.get('volume')
        else:
            volumes = binds

        if not volumes:
            return None, None

        vol_list = list()
        vol_dict = dict()

        for vol in volumes:
            if not vol:
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

    @abstractmethod
    def build_ulimits(self, ulimits):
        pass

    @abstractmethod
    def create_container(self):
        pass

    @abstractmethod
    def recreate_or_restart_container(self):
        pass

    @abstractmethod
    def start_container(self):
        pass

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

    @abstractmethod
    def stop_container(self):
        pass

    @abstractmethod
    def stop_and_remove_container(self):
        pass

    @abstractmethod
    def restart_container(self):
        pass

    @abstractmethod
    def create_volume(self):
        pass

    @abstractmethod
    def remove_volume(self):
        pass

    @abstractmethod
    def remove_image(self):
        pass

    @abstractmethod
    def ensure_image(self):
        pass

    def _inject_env_var(self, environment_info):
        newenv = {
            'KOLLA_SERVICE_NAME': self.params.get('name').replace('_', '-')
        }
        environment_info.update(newenv)
        return environment_info

    def _format_env_vars(self):
        env = self._inject_env_var(self.params.get('environment'))
        return {k: "" if env[k] is None else env[k] for k in env}
