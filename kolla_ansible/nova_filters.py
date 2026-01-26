# Copyright (c) 2019 StackHPC Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import jinja2
import re

from kolla_ansible import exception


def extract_cell(list_cells_cli_output, cell_name):
    """Extract cell settings from nova_manage CLI

    This filter tries to extract the cell settings for the specified cell
    from the output of the command:
    nova-manage cell_v2 list_cells --verbose
    If the cell is not registered, nothing is returned.

    An example line from this command for a cell with no name looks like this:

    |  | 68a3f49e-27ec-422f-9e2e-2a4e5dc8291b | rabbit://openstack:password@1.2.3.4:5672 | mysql+pymysql://nova:password@1.2.3.4:3306/nova |  False   |  # noqa

    And for a cell with a name:

    | cell1 | 68a3f49e-27ec-422f-9e2e-2a4e5dc8291b | rabbit://openstack:password@1.2.3.4:5672 | mysql+pymysql://nova:password@1.2.3.4:3306/nova |  False   |  # noqa

    """
    # NOTE(priteau): regexp doesn't support passwords containing spaces
    p = re.compile(
        r'\| +(?P<cell_name>[^ ]+)? +'
        r'\| +(?P<cell_uuid>[0-9a-f\-]+) +'
        r'\| +(?P<cell_message_queue>[^ ]+) +'
        r'\| +(?P<cell_database>[^ ]+) +'
        r'\| +(?P<cell_disabled>[^ ]+) +'
        r'\|$')
    cells = []
    for line in list_cells_cli_output['stdout_lines']:
        match = p.match(line)
        if match:
            # If there is no cell name, we get None in the cell_name match
            # group. Use an empty string to match the default cell.
            match_cell_name = match.group('cell_name') or ""
            if match_cell_name == cell_name:
                cells.append(match.groupdict())
    if len(cells) > 1:
        raise jinja2.TemplateRuntimeError(
            "Cell: {} has duplicates. "
            "Manual cleanup required.".format(cell_name))
    return cells[0] if cells else None


def namespace_haproxy_for_cell(services, cell_name):
    """Add namespacing to HAProxy configuration for a cell.

    :param services: dict defining service configuration.
    :param cell_name: name of the cell, or empty if cell has no name.
    :returns: the services dict, with haproxy configuration modified to
            provide namespacing between cells.
    """
    def _namespace(name):
        # Backwards compatibility - no cell name suffix for cells without a
        # name.
        return "{}_{}".format(name, cell_name) if cell_name else name

    # Service name must be namespaced as loadbalancer-config uses this as the
    # config file name.
    services = {
        _namespace(service_name): service
        for service_name, service in services.items()
    }
    for service in services.values():
        if service.get('haproxy'):
            service['haproxy'] = {
                _namespace(name): service['haproxy'][name]
                for name in service['haproxy']
            }
    return services


def get_expected_ironic_compute_services(ironic_compute_batch_info,
                                         multi_compute_conf,
                                         nova_cell_compute_ironic_group):
    """Return a List of expected Ironic compute services

      :param ironic_compute_batch_info: A dict containing configuration
             information about Ironic Compute hosts.
      :param multi_compute_conf: Ironic multi-compute config
      :param nova_cell_compute_ironic_group: Ansible group name for
             nova-compute-ironic. Eg. 'nova-compute-ironic'.
      :returns: A list of Nova Compute Ironic service hostnames.
    """
    classic_info = ironic_compute_batch_info['classic']
    multi_compute_info = ironic_compute_batch_info['multi']
    if len(multi_compute_conf) == 0:
        return [f'{host}-ironic' for host in classic_info]

    expected_services = []
    group_prefix = nova_cell_compute_ironic_group + '-'
    for host in multi_compute_info:
        iterate_vars = [
            int(group.split(group_prefix)[1])
            for group in host if group_prefix in group]
        for i in iterate_vars:
            try:
                service_conf = multi_compute_conf[i - 1]
            except IndexError:
                raise exception.FilterError(
                    "Unable to look up multi-compute Ironic config for "
                    "{g}-{i} inventory group. Check that "
                    "nova_multi_compute_ironic_config has an entry for "
                    "each defined group.".format(
                        g=nova_cell_compute_ironic_group,
                        i=i))
            expected_services.append(
                _get_expected_compute_service_name(service_conf))
    return expected_services


def _get_expected_compute_service_name(service_conf):
    custom_host = service_conf.get('custom_host')
    if custom_host:
        return f"{custom_host}-ironic"
    cg = service_conf.get('conductor_group', 'default')
    sk = service_conf.get('shard_key', 'default')
    return f"{cg}-{sk}-ironic"


def get_filters():
    return {
        "extract_cell": extract_cell,
        "namespace_haproxy_for_cell": namespace_haproxy_for_cell,
        "get_expected_ironic_compute_services": get_expected_ironic_compute_services,  # noqa
    }
