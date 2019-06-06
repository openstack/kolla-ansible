#!/usr/bin/env python

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

import imp
import os
import sys

from oslotest import base

this_dir = os.path.dirname(sys.modules[__name__].__file__)
file_under_test = os.path.join(this_dir, '..', 'ansible',
                               'roles', 'keystone', 'files',
                               'fernet_rotate_cron_generator.py')
generator = imp.load_source('generator', file_under_test)


class FernetRotateCronGeneratorTest(base.BaseTestCase):

    def _test(self, host_index, total_hosts, total_rotation_mins, expected):
        result = generator.generate(host_index, total_hosts,
                                    total_rotation_mins)
        self.assertEqual(expected, result)

    def test_invalid_index(self):
        expected = []
        self._test(1, 0, 0, expected)

    # total_rotation_mins == WEEK_SPAN:

    def test_1_week_1_host(self):
        expected = [{"min": 0, "hour": 0, "day": 0}]
        self._test(0, 1, 7 * 24 * 60, expected)

    def test_1_week_2_hosts(self):
        expected = [{"min": 0, "hour": 0, "day": 0}]
        self._test(0, 2, 7 * 24 * 60, expected)

        expected = [{"min": 0, "hour": 12, "day": 3}]
        self._test(1, 2, 7 * 24 * 60, expected)

    # total_rotation_mins == DAY_SPAN:

    def test_1_day_1_host(self):
        expected = [{"min": 0, "hour": 0, "day": "*"}]
        self._test(0, 1, 24 * 60, expected)

    def test_1_day_2_hosts(self):
        expected = [{"min": 0, "hour": 0, "day": "*"}]
        self._test(0, 2, 24 * 60, expected)

        expected = [{"min": 0, "hour": 12, "day": "*"}]
        self._test(1, 2, 24 * 60, expected)

    # total_rotation_mins % HOUR_SPAN == 0:

    def test_1_hour_1_host(self):
        # nit: This could be a single hour: '*'.
        expected = [{"min": 0, "hour": hour, "day": "*"}
                    for hour in range(24)]
        self._test(0, 1, 60, expected)

    def test_1_hour_2_hosts(self):
        expected = [{"min": 0, "hour": hour, "day": "*"}
                    for hour in range(24)]
        self._test(0, 2, 60, expected)

        expected = [{"min": 30, "hour": hour, "day": "*"}
                    for hour in range(24)]
        self._test(1, 2, 60, expected)

    def test_2_hours_1_host(self):
        expected = [{"min": 0, "hour": hour, "day": "*"}
                    for hour in range(0, 24, 2)]
        self._test(0, 1, 2 * 60, expected)

    def test_2_hours_2_hosts(self):
        expected = [{"min": 0, "hour": hour, "day": "*"}
                    for hour in range(0, 24, 2)]
        self._test(0, 2, 2 * 60, expected)

        expected = [{"min": 0, "hour": hour, "day": "*"}
                    for hour in range(1, 24, 2)]
        self._test(1, 2, 2 * 60, expected)

    def test_2_days_1_host(self):
        # FIXME: Anything greater than 1 day (except 1 week) returns no jobs.
        expected = []
        self._test(0, 1, 2 * 24 * 60, expected)

    def test_2_days_2_hosts(self):
        # FIXME: Anything greater than 1 day (except 1 week) returns no jobs.
        expected = []
        self._test(0, 2, 2 * 24 * 60, expected)

        expected = []
        self._test(1, 2, 2 * 24 * 60, expected)

    # total_rotation_mins % MINUTE_SPAN == 0:

    def test_1_minute_1_host(self):
        # This could be a single hour: '*'.
        expected = [{"min": min, "hour": "*", "day": "*"}
                    for min in range(60)]
        self._test(0, 1, 1, expected)

    def test_1_minute_2_hosts(self):
        # This is kind of broken, but its an edge case so nevermind.
        expected = [{"min": min, "hour": "*", "day": "*"}
                    for min in range(60)]
        self._test(0, 2, 1, expected)

        expected = [{"min": min, "hour": "*", "day": "*"}
                    for min in range(60)]
        self._test(1, 2, 1, expected)

    def test_2_minutes_1_host(self):
        expected = [{"min": min, "hour": "*", "day": "*"}
                    for min in range(0, 60, 2)]
        self._test(0, 1, 2, expected)

    def test_2_minutes_2_hosts(self):
        expected = [{"min": min, "hour": "*", "day": "*"}
                    for min in range(0, 60, 2)]
        self._test(0, 2, 2, expected)

        expected = [{"min": min, "hour": "*", "day": "*"}
                    for min in range(1, 60, 2)]
        self._test(1, 2, 2, expected)

    def test_61_minutes_1_host(self):
        # FIXME: Anything greater than 1 hour (unless an integer number of
        # hours) returns no jobs.
        expected = []
        self._test(0, 1, 61, expected)

    def test_61_minutes_2_hosts(self):
        # FIXME: Anything greater than 1 hour (unless an integer number of
        # hours) returns no jobs.
        expected = []
        self._test(0, 1, 61, expected)

        expected = []
        self._test(1, 2, 61, expected)
