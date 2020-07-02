# Copyright (c) 2020 StackHPC Ltd.
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

import os.path


def customise_fluentd(default_paths, customised_paths):
    """Return a sorted list of templates for fluentd.

    :param default_paths: Iterable of default template paths.
    :param customised_paths: Iterable of customised template paths.
    :returns: A sorted combined list of template paths.
    """

    def _basename_no_ext(path):
        """Return the basename of a path, stripping off any extension."""
        return os.path.splitext(os.path.basename(path))[0]

    customised_file_names = {os.path.basename(f) for f in customised_paths}
    # Starting with the default paths, remove any that have been overridden,
    # ignoring the .j2 extension of default paths.
    result = {f for f in default_paths
              if _basename_no_ext(f) not in customised_file_names}
    # Add all customised paths.
    result.update(customised_paths)
    # Sort by the basename of the paths.
    return sorted(result, key=os.path.basename)


def get_filters():
    return {
        "customise_fluentd": customise_fluentd,
    }
