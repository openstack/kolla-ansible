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

from kolla_ansible.exception import FilterError


def put_address_in_context(address, context):
    """puts address in context

    :param address: the address to contextify
    :param context: describes context in which the address appears,
                    either 'url' or 'memcache',
                    affects only IPv6 addresses format
    :returns: string with address in proper context
    """

    if context not in ['url', 'memcache']:
        raise FilterError("Unknown context '{context}'"
                          .format(context=context))

    if ':' not in address:
        return address

    # must be IPv6 raw address

    if context == 'url':
        return '[{address}]'.format(address=address)
    elif context == 'memcache':
        return 'inet6:[{address}]'.format(address=address)

    return address
