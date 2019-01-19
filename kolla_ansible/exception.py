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

try:
    from ansible.errors import AnsibleFilterError
except ImportError:
    # NOTE(mgoddard): For unit testing we don't depend on Ansible since it is
    # not in global requirements.
    AnsibleFilterError = Exception


class FilterError(AnsibleFilterError):
    """Error during execution of a jinja2 filter."""
