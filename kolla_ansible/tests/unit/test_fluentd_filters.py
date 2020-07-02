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

import unittest

from kolla_ansible.fluentd_filters import customise_fluentd


class TestFilters(unittest.TestCase):

    def test_customise_fluentd_no_files(self):
        default_files = [
        ]
        customised_files = [
        ]
        expected = [
        ]
        result = customise_fluentd(default_files, customised_files)
        self.assertEqual(expected, result)

    def test_customise_fluentd_no_customised_files(self):
        default_files = [
            "foo/bar.conf.j2"
        ]
        customised_files = [
        ]
        expected = [
            "foo/bar.conf.j2"
        ]
        result = customise_fluentd(default_files, customised_files)
        self.assertEqual(expected, result)

    def test_customise_fluentd_no_default_files(self):
        default_files = [
        ]
        customised_files = [
            "foo/bar.conf"
        ]
        expected = [
            "foo/bar.conf"
        ]
        result = customise_fluentd(default_files, customised_files)
        self.assertEqual(expected, result)

    def test_customise_fluentd_both(self):
        default_files = [
            "foo/bar.conf.j2"
        ]
        customised_files = [
            "baz/qux.conf"
        ]
        expected = [
            "foo/bar.conf.j2",
            "baz/qux.conf"
        ]
        result = customise_fluentd(default_files, customised_files)
        self.assertEqual(expected, result)

    def test_customise_fluentd_override(self):
        default_files = [
            "foo/bar.conf.j2"
        ]
        customised_files = [
            "baz/bar.conf"
        ]
        expected = [
            "baz/bar.conf"
        ]
        result = customise_fluentd(default_files, customised_files)
        self.assertEqual(expected, result)

    def test_customise_fluentd_both_with_override(self):
        default_files = [
            "foo/bar.conf.j2",
            "baz/qux.conf.j2"
        ]
        customised_files = [
            "baz/bar.conf"
        ]
        expected = [
            "baz/bar.conf",
            "baz/qux.conf.j2"
        ]
        result = customise_fluentd(default_files, customised_files)
        self.assertEqual(expected, result)
