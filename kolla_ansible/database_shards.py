# -*- coding: utf-8 -*-
#
# Copyright 2022 Michal Arbet (kevko)
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

from jinja2.filters import pass_context
from jinja2.runtime import Undefined

from kolla_ansible.exception import FilterError
from kolla_ansible.helpers import _call_bool_filter


@pass_context
def database_shards_info(context, hostnames):
    """returns dict with database shards info

       Returned dict looks as example below:

       "database_shards_info": {
           "shards": {
               "0": {
                   "hosts": [
                       "controller0",
                       "controller1",
                       "controller2"
                   ]
               },
               "1": {
                   "hosts": [
                       "controller3",
                       "controller4",
                       "controller5"
                   ]
               }
           },
           "users": [
               {
                   "password": "secret",
                   "shard_id": "0",
                   "user": "root_shard_0"
               },
               {
                   "password": "secret",
                   "shard_id": "0",
                   "user": "backup_shard_0"
               },
               {
                   "password": "secret",
                   "shard_id": "1",
                   "user": "root_shard_1"
               },
               {
                   "password": "secret",
                   "shard_id": "1",
                   "user": "backup_shard_1"
               }
           ]
       }

    :param context: Jinja2 Context
    :param hostnames: List of database hosts
    :returns: Dict with database shards info
    """

    hostvars = context.get('hostvars')
    if isinstance(hostvars, Undefined):
        raise FilterError("'hostvars' variable is unavailable")

    shards_info = {'shards': {}, 'users': []}

    for hostname in hostnames:

        host = hostvars.get(hostname)
        if isinstance(host, Undefined):
            raise FilterError(f"'{hostname}' not in 'hostvars'")

        host_shard_id = host.get('mariadb_shard_id')
        if host_shard_id is None:
            raise FilterError("'mariadb_shard_id' is undefined "
                              f"for host '{hostname}'")
        else:
            host_shard_id = str(host_shard_id)

        if host_shard_id not in shards_info['shards']:
            shards_info['shards'][host_shard_id] = {'hosts': [hostname]}

            backup_enabled = host.get('enable_mariabackup')
            if backup_enabled is None:
                raise FilterError("'enable_mariabackup' variable is "
                                  "unavailable")
            backup_enabled = _call_bool_filter(context, backup_enabled)

            db_password = host.get('database_password')
            if db_password is None:
                raise FilterError("'database_password' variable is "
                                  "unavailable")

            db_root_prefix = host.get('mariadb_shard_root_user_prefix')
            if db_root_prefix is None:
                raise FilterError("'mariadb_shard_root_user_prefix' variable "
                                  "is unavailable")
            db_user = f"{db_root_prefix}{host_shard_id}"
            user_dict = {'password': db_password, 'user': db_user,
                         'shard_id': host_shard_id}
            shards_info['users'].append(user_dict)

            if backup_enabled:
                db_backup_prefix = host.get('mariadb_shard_backup_user_prefix')
                if db_backup_prefix is None:
                    raise FilterError("'mariadb_shard_backup_user_prefix' "
                                      "variable is unavailable")
                db_user = f"{db_backup_prefix}{host_shard_id}"
                db_password = host.get('mariadb_backup_database_password')
                user_dict = {'password': db_password, 'user': db_user,
                             'shard_id': host_shard_id}
                shards_info['users'].append(user_dict)
        else:
            shards_info['shards'][host_shard_id]['hosts'].append(hostname)

    return shards_info
