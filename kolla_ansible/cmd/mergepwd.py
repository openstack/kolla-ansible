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
import os
import stat
import sys
import yaml


def mergepwd(old, new, final, clean=False):
    with open(old, "r") as old_file:
        old_passwords = yaml.safe_load(old_file)

    if os.stat(old).st_mode & stat.S_IROTH:
        print(f"WARNING: Passwords file \"{old}\" is world-readable.")

    if os.stat(old).st_mode & stat.S_IWOTH:
        print(f"WARNING: Passwords file \"{old}\" is world-writeable.")

    with open(new, "r") as new_file:
        new_passwords = yaml.safe_load(new_file)

    if os.stat(new).st_mode & stat.S_IROTH:
        print(f"WARNING: Passwords file \"{new}\" is world-readable.")

    if os.stat(new).st_mode & stat.S_IWOTH:
        print(f"WARNING: Passwords file \"{new}\" is world-writeable.")

    if not isinstance(old_passwords, dict):
        print("ERROR: Old passwords file not in expected key/value format")
        sys.exit(1)

    if not isinstance(new_passwords, dict):
        print("ERROR: New passwords file not in expected key/value format")
        sys.exit(1)

    if clean:
        # keep only new keys
        for key in new_passwords:
            if key in old_passwords:
                new_passwords[key] = old_passwords[key]
    else:
        # old behavior
        new_passwords.update(old_passwords)

    try:
        os.remove(final)
    except OSError:
        pass

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    mode = 0o640

    with os.fdopen(os.open(final, flags, mode=mode), 'w') as destination:
        yaml.safe_dump(new_passwords, destination, default_flow_style=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", help="old password file", required=True)
    parser.add_argument("--new", help="new password file", required=True)
    parser.add_argument("--final", help="merged password file", required=True)
    parser.add_argument("--clean",
                        help="clean (keep only new keys)",
                        action='store_true')
    args = parser.parse_args()
    mergepwd(args.old, args.new, args.final, args.clean)


if __name__ == '__main__':
    main()
