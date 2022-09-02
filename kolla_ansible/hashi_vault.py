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

import os
import sys

import hvac


def hashicorp_vault_client(vault_namespace, vault_addr, vault_role_id,
                           vault_secret_id, vault_token, vault_cacert):
    """Connect to a Vault sever and create a client.

    :param vault_namespace: Vault namespace (enterprise only).
    :param vault_addr: Address to connect to an existing Hashicorp Vault.
    :param vault_role_id: Role-ID to authenticate to Vault. This must be used
    in conjunction with --secret-id.
    :param vault_secret_id: Secret-ID to authenticate to Vault. This must be
    used in conjunction with --role-id.
    :param vault_token: Vault token to authenticate to Vault.
    :param vault_cacert: Path to CA certificate file.
    :returns: Hashicorp Vault Client (hvac.Client).
    """

    if any([vault_role_id, vault_secret_id]):
        if vault_token:
            print("ERROR: Vault token cannot be used at the same time as "
                  "role-id and secret-id")
            sys.exit(1)
        if not all([vault_role_id, vault_secret_id]):
            print("ERROR: role-id and secret-id must be provided together")
            sys.exit(1)
    elif not vault_token:
        print("ERROR: You must provide either a Vault token or role-id and "
              "secret-id")
        sys.exit(1)

    # Authenticate to Hashicorp Vault
    if vault_cacert != "":
        os.environ['REQUESTS_CA_BUNDLE'] = vault_cacert

    if vault_token != "":  # nosec
        client = hvac.Client(url=vault_addr, token=vault_token,
                             namespace=vault_namespace)
    else:
        client = hvac.Client(url=vault_addr, namespace=vault_namespace)
        client.auth.approle.login(role_id=vault_role_id,
                                  secret_id=vault_secret_id)

    if not client.is_authenticated():
        print('Failed to authenticate to vault')
        sys.exit(1)

    return client
