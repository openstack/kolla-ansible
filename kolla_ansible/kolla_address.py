# -*- coding: utf-8 -*-
#
# Copyright 2019 Radosław Piliszek (yoctozepto)
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

import ipaddress

from jinja2.filters import pass_context
from jinja2.runtime import Undefined

from kolla_ansible.exception import FilterError
from kolla_ansible.helpers import _call_bool_filter


@pass_context
def kolla_address(context, network_name, hostname=None, override_var=None):
    """returns IP address on the requested network

    The output is affected by '<network_name>_*' variables:
    '<network_name>_interface' sets the interface to obtain address for.
    '<network_name>_address_family' controls the address family (ipv4/ipv6).

    :param context: Jinja2 Context
    :param network_name: string denoting the name of the network to get IP
                         address for, e.g. 'api'
    :param hostname: to override host which address is retrieved for
    :param override_var: optional name of a host variable that can be used
                         to override the IP address
    :returns: string with IP address
    """

    # NOTE(yoctozepto): watch out as Jinja2 'context' behaves not exactly like
    # the python 'dict' (but mimics it most of the time)
    # for example it returns a special object of type 'Undefined' instead of
    # 'None' or value specified as default for 'get' method
    # 'HostVars' shares this behavior

    if hostname is None:
        hostname = context.get('inventory_hostname')
        if isinstance(hostname, Undefined):
            raise FilterError("'inventory_hostname' variable is unavailable")

    hostvars = context.get('hostvars')
    if hostvars is None or isinstance(hostvars, Undefined):
        raise FilterError("'hostvars' variable is unavailable")

    host = hostvars.get(hostname)
    if isinstance(host, Undefined):
        raise FilterError("'{hostname}' not in 'hostvars'"
                          .format(hostname=hostname))

    del hostvars  # remove for clarity (no need for other hosts)

    if override_var is not None:
        if override_var in host:
            try:
                # Use ipaddress to test IPv4/6 validity of
                # the string returned from override_var and
                # return the string-formatted, valid IP address
                ip = ipaddress.ip_address(host[override_var])
                return format(ip)
            except ValueError:
                # Catch ValueError from ipaddress and make the
                # output more useful for operators
                raise FilterError("variable '{override_var}' for "
                                  "host '{hostname}' is set to "
                                  "'{value}', which is not a valid "
                                  "IPv4 or IPv6 address"
                                  .format(override_var=override_var,
                                          hostname=hostname,
                                          value=host[override_var]))

    # NOTE(yoctozepto): variable "host" will *not* return Undefined
    # same applies to all its children (act like plain dictionary)

    interface_name = host.get(network_name + '_interface')
    if interface_name is None:
        raise FilterError("Interface name undefined "
                          "for network '{network_name}' "
                          "(set '{network_name}_interface')"
                          .format(network_name=network_name))

    address_family = host.get(network_name + '_address_family')
    if address_family is None:
        raise FilterError("Address family undefined "
                          "for network '{network_name}' "
                          "(set '{network_name}_address_family')"
                          .format(network_name=network_name))
    address_family = address_family.lower()
    if address_family not in ['ipv4', 'ipv6']:
        raise FilterError("Unknown address family '{address_family}' "
                          "for network '{network_name}'"
                          .format(address_family=address_family,
                                  network_name=network_name))

    ansible_interface_name = interface_name.replace('-', '_')
    interface = host['ansible_facts'].get(ansible_interface_name)
    if interface is None:
        raise FilterError("Interface '{interface_name}' "
                          "not present "
                          "on host '{hostname}'"
                          .format(interface_name=interface_name,
                                  hostname=hostname))

    af_interface = interface.get(address_family)
    if af_interface is None:
        raise FilterError("Address family '{address_family}' undefined "
                          "on interface '{interface_name}' "
                          "for host: '{hostname}'"
                          .format(address_family=address_family,
                                  interface_name=interface_name,
                                  hostname=hostname))

    if address_family == 'ipv4':
        address = af_interface.get('address')
    elif address_family == 'ipv6':
        # ipv6 has no concept of a secondary address
        # explicitly exclude the vip addresses
        # to avoid excluding all /128

        haproxy_enabled = host.get('enable_haproxy')
        if haproxy_enabled is None:
            raise FilterError("'enable_haproxy' variable is unavailable")
        haproxy_enabled = _call_bool_filter(context, haproxy_enabled)

        if haproxy_enabled:
            vip_addresses = [
                host.get('kolla_internal_vip_address'),
                host.get('kolla_external_vip_address'),
            ]
        else:
            # no addresses are virtual (kolla-wise)
            vip_addresses = []

        global_ipv6_addresses = [x for x in af_interface if
                                 x['scope'] == 'global' and
                                 x['address'] not in vip_addresses]

        if global_ipv6_addresses:
            address = global_ipv6_addresses[0]['address']
        else:
            address = None

    if address is None:
        raise FilterError("{address_family} address missing "
                          "on interface '{interface_name}' "
                          "for host '{hostname}'"
                          .format(address_family=address_family,
                                  interface_name=interface_name,
                                  hostname=hostname))

    return address
