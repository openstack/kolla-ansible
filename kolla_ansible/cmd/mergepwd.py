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

import argparse
import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", help="old password file", required=True)
    parser.add_argument("--new", help="new password file", required=True)
    parser.add_argument("--final", help="merged password file", required=True)
    args = parser.parse_args()

    with open(args.old, "r") as old_file:
        old_passwords = yaml.safe_load(old_file)

    with open(args.new, "r") as new_file:
        new_passwords = yaml.safe_load(new_file)

    new_passwords.update(old_passwords)

    with open(args.final, "w") as destination:
        yaml.safe_dump(new_passwords, destination, default_flow_style=False)


if __name__ == '__main__':
    main()
