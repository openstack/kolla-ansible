# -*- coding: utf-8 -*-
#
# Copyright 2022 StackHPC Ltd.
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

from kolla_ansible.put_address_in_context import put_address_in_context


def kolla_url(fqdn, protocol, port, path='', context='url'):
    """generates url

    :param fqdn:
    :param protocol: http, ws, https or wss
    :param port: port (omits 80 on http and 443 on https in output)
    :param path: path - optional
    :returns: string with url
    """

    fqdn = put_address_in_context(fqdn, context)
    port = int(port)

    if ((protocol == 'http' and port == 80) or
       (protocol == 'https' and port == 443) or
       (protocol == 'ws' and port == 80) or
       (protocol == 'wss' and port == 443)):
        address = f"{protocol}://{fqdn}{path}"
    else:
        address = f"{protocol}://{fqdn}:{port}{path}"

    return address
