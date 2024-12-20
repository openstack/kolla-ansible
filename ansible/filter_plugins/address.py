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

from kolla_ansible.kolla_address import kolla_address
from kolla_ansible.kolla_url import kolla_url
from kolla_ansible.put_address_in_context import put_address_in_context


class FilterModule(object):
    """IP address filters"""

    def filters(self):
        return {
            'kolla_address': kolla_address,
            'kolla_url': kolla_url,
            'put_address_in_context': put_address_in_context,
        }
