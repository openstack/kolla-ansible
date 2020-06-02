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

# This module creates a list of cron intervals for a node in a group of nodes
# to ensure each node runs a cron in round robbin style.
import argparse
import json
import sys

MINUTE_SPAN = 1
HOUR_SPAN = 60
DAY_SPAN = 24 * HOUR_SPAN
WEEK_SPAN = 7 * DAY_SPAN


class RotationIntervalTooLong(Exception):
    pass


def json_exit(msg=None, failed=False, changed=False):
    if type(msg) is not dict:
        msg = {'msg': str(msg)}
    msg.update({'failed': failed, 'changed': changed})
    print(json.dumps(msg))
    sys.exit()


def generate(host_index, total_hosts, total_rotation_mins):
    min = '*'  # 0-59
    hour = '*'  # 0-23
    day = '*'  # 0-6 (day of week)
    crons = []

    if host_index >= total_hosts:
        return crons

    # We need to rotate the key every total_rotation_mins minutes.
    # When there are N hosts, each host should rotate once every N *
    # total_rotation_mins minutes, in a round-robin manner.
    # We can generate a cycle for index 0, then add an offset specific to each
    # host.
    # NOTE: Minor under-rotation is better than over-rotation since tokens
    # may become invalid if keys are over-rotated.
    host_rotation_mins = total_rotation_mins * total_hosts
    host_rotation_offset = total_rotation_mins * host_index

    # Can't currently rotate less than once per week.
    if total_rotation_mins > WEEK_SPAN:
        msg = ("Unable to schedule fernet key rotation with an interval "
               "greater than 1 week divided by the number of hosts")
        raise RotationIntervalTooLong(msg)

    # Build crons multiple of a day
    elif host_rotation_mins > DAY_SPAN:
        time = host_rotation_offset
        while time + total_rotation_mins <= WEEK_SPAN:
            day = time // DAY_SPAN
            hour = time % HOUR_SPAN
            min = time % HOUR_SPAN
            crons.append({'min': min, 'hour': hour, 'day': day})

            time += host_rotation_mins

    # Build crons for multiple of an hour
    elif host_rotation_mins > HOUR_SPAN:
        time = host_rotation_offset
        while time + total_rotation_mins <= DAY_SPAN:
            hour = time // HOUR_SPAN
            min = time % HOUR_SPAN
            crons.append({'min': min, 'hour': hour, 'day': day})

            time += host_rotation_mins

    # Build crons for multiple of a minute
    else:
        time = host_rotation_offset
        while time + total_rotation_mins <= HOUR_SPAN:
            min = time // MINUTE_SPAN
            crons.append({'min': min, 'hour': hour, 'day': day})

            time += host_rotation_mins

    return crons


def main():
    parser = argparse.ArgumentParser(description='''Creates a list of cron
        intervals for a node in a group of nodes to ensure each node runs
        a cron in round robin style.''')
    parser.add_argument('-t', '--time',
                        help='Time in minutes for a key rotation cycle',
                        required=True,
                        type=int)
    parser.add_argument('-i', '--index',
                        help='Index of host starting from 0',
                        required=True,
                        type=int)
    parser.add_argument('-n', '--number',
                        help='Number of hosts',
                        required=True,
                        type=int)
    args = parser.parse_args()
    try:
        jobs = generate(args.index, args.number, args.time)
    except Exception as e:
        json_exit(str(e), failed=True)
    json_exit({'cron_jobs': jobs})


if __name__ == "__main__":
    main()
