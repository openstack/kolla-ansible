#!/usr/bin/env python3

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

import hvac
import yaml

from kolla_ansible.hashi_vault import hashicorp_vault_client


def readpwd(passwords_file, vault_kv_path, vault_mount_point, vault_namespace,
            vault_addr, vault_role_id, vault_secret_id, vault_token,
            vault_cacert):

    with open(passwords_file, 'r') as f:
        passwords = yaml.safe_load(f.read())

    if os.stat(passwords_file).st_mode & stat.S_IROTH:
        print(f"WARNING: Passwords file \"{passwords_file}\" is"
              " world-readable. The permissions will be changed.")

    if os.stat(passwords_file).st_mode & stat.S_IWOTH:
        print(f"WARNING: Passwords file \"{passwords_file}\" is"
              " world-writeable. The permissions will be changed.")

    if not isinstance(passwords, dict):
        print("ERROR: Passwords file not in expected key/value format")
        sys.exit(1)

    client = hashicorp_vault_client(vault_namespace, vault_addr, vault_role_id,
                                    vault_secret_id, vault_token, vault_cacert)

    vault_kv_passwords = dict()
    for password_key in passwords:
        try:
            password_data = client.secrets.kv.v2.read_secret_version(
                mount_point=vault_mount_point,
                path="{}/{}".format(vault_kv_path, password_key))
        except hvac.exceptions.InvalidPath:
            # Ignore passwords that are not found in Vault
            print("WARNING: '%s' not found in Vault" % password_key)
            vault_kv_passwords[password_key] = None
            continue
        try:
            vault_kv_passwords[password_key] =\
                password_data['data']['data']['password']
        except KeyError:
            vault_kv_passwords[password_key] = password_data['data']['data']

    try:
        os.remove(passwords_file)
    except OSError:
        pass

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    mode = 0o640

    with os.fdopen(os.open(passwords_file, flags, mode=mode), 'w') as f:
        yaml.safe_dump(vault_kv_passwords, f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p', '--passwords', type=str,
        default=os.path.abspath('/etc/kolla/passwords.yml'),
        help='Path to the passwords.yml file')
    parser.add_argument(
        '-kv', '--vault-mount-point', type=str,
        default='kv',
        help='Path to the KV mount point')
    parser.add_argument(
        '-kvp', '--vault-kv-path', type=str,
        default='kolla_passwords',
        help='Path to store passwords within your configured KV mount point')
    parser.add_argument(
        '-n', '--vault-namespace', type=str,
        default='',
        help='Vault namespace (enterprise only)')
    parser.add_argument(
        '-v', '--vault-addr', type=str,
        required=True,
        help='Address to connect to an existing Hashicorp Vault')
    parser.add_argument(
        '-r', '--vault-role-id', type=str,
        default='',
        help='Role-ID to authenticate to Vault. This must be used in '
             'conjunction with --secret-id')
    parser.add_argument(
        '-s', '--vault-secret-id', type=str,
        default='',
        help='Secret-ID to authenticate to Vault. This must be used in '
             'conjunction with --role-id')
    parser.add_argument(
        '-t', '--vault-token', type=str,
        default='',
        help='Vault token to authenticate to Vault')
    parser.add_argument(
        '-c', '--vault-cacert', type=str,
        default='',
        help='Path to CA certificate file')

    args = parser.parse_args()
    passwords_file = os.path.expanduser(args.passwords)
    vault_kv_path = args.vault_kv_path
    vault_mount_point = args.vault_mount_point
    vault_namespace = args.vault_namespace
    vault_addr = args.vault_addr
    vault_role_id = args.vault_role_id
    vault_secret_id = args.vault_secret_id
    vault_token = args.vault_token
    vault_cacert = os.path.expanduser(args.vault_cacert)

    readpwd(passwords_file, vault_kv_path, vault_mount_point, vault_namespace,
            vault_addr, vault_role_id, vault_secret_id, vault_token,
            vault_cacert)


if __name__ == '__main__':
    main()
