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

from kolla_ansible import exception
from kolla_ansible.helpers import _call_bool_filter


@jinja2.pass_context
def service_enabled(context, service):
    """Return whether a service is enabled.

    :param context: Jinja2 Context object.
    :param service: Service definition, dict.
    :returns: A boolean.
    """
    enabled = service.get('enabled')
    if enabled is None:
        raise exception.FilterError(
            "Service definition for '%s' does not have an 'enabled' attribute"
            % service.get("container_name", "<unknown>"))
    return _call_bool_filter(context, enabled)


@jinja2.pass_context
def extract_haproxy_services(context, services):
    """Return a Dict of haproxy services

      :param context: Jinja2 Context object.
      :param service: Services definition, dict.
      :returns: A Dict.
    """
    haproxy = {}
    for key in services:
        service = services.get(key)
        if service_enabled(context, service):
            service_haproxy = service.get('haproxy')
            if service_haproxy:
                if not set(haproxy).isdisjoint(set(service_haproxy)):
                    raise exception.FilterError(
                        "haproxy service names should be unique")
                haproxy.update(service_haproxy)

    return haproxy


@jinja2.pass_context
def service_mapped_to_host(context, service):
    """Return whether a service is mapped to this host.

    There are two ways to describe the service to host mapping. The most common
    is via a 'group' attribute, where the service is mapped to all hosts in the
    group. The second approach is via a 'host_in_groups' attribute, which is a
    boolean expression which should be evaluated for every host. The latter
    approach takes precedence over the first.

    :param context: Jinja2 Context object.
    :param service: Service definition, dict.
    :returns: A boolean.
    """
    host_in_groups = service.get("host_in_groups")
    if host_in_groups is not None:
        return _call_bool_filter(context, host_in_groups)

    group = service.get("group")
    if group is not None:
        return group in context.get("group_names") or group == "all"

    raise exception.FilterError(
        "Service definition for '%s' does not have a 'group' or "
        "'host_in_groups' attribute" %
        service.get("container_name", "<unknown>"))


@jinja2.pass_context
def service_enabled_and_mapped_to_host(context, service):
    """Return whether a service is enabled and mapped to this host.

    :param context: Jinja2 Context object.
    :param service: Service definition, dict.
    :returns: A boolean.
    """
    return (service_enabled(context, service) and
            service_mapped_to_host(context, service))


@jinja2.pass_context
def select_services_enabled_and_mapped_to_host(context, services):
    """Select services that are enabled and mapped to this host.

    :param context: Jinja2 Context object.
    :param services: Service definitions, dict.
    :returns: A dict containing enabled services mapped to this host.
    """
    return {service_name: service
            for service_name, service in services.items()
            if service_enabled_and_mapped_to_host(context, service)}


def get_filters():
    return {
        "extract_haproxy_services": extract_haproxy_services,
        "service_enabled": service_enabled,
        "service_mapped_to_host": service_mapped_to_host,
        "service_enabled_and_mapped_to_host": (
            service_enabled_and_mapped_to_host),
        "select_services_enabled_and_mapped_to_host": (
            select_services_enabled_and_mapped_to_host),
    }
