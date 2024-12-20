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

import unittest

import jinja2

from kolla_ansible.database_shards import database_shards_info
from kolla_ansible.exception import FilterError

from kolla_ansible.tests.unit.helpers import _to_bool


class TestKollaDatabaseShardsInfoFilter(unittest.TestCase):

    def setUp(self):
        # Bandit complains about Jinja2 autoescaping without nosec.
        self.env = jinja2.Environment()  # nosec
        self.env.filters['bool'] = _to_bool

    def _make_context(self, parent):
        return self.env.context_class(
            self.env, parent=parent, name='dummy', blocks={})

    def test_missing_shard_id(self):
        hostnames = ["primary"]
        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                }
            }
        })
        self.assertRaises(FilterError, database_shards_info,
                          context, hostnames)

    def test_valid_shards_info_with_backup_user(self):
        hostnames = ['primary', 'secondary1', 'secondary2']
        enable_mariabackup = 'yes'
        root_prefix = 'root_shard_'
        backup_prefix = 'backup_shard_'
        db_cred = 'SECRET'
        backup_db_cred = 'SECRET1'
        db_shards = ['0', '1']

        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'mariadb_shard_id': db_shards[0],
                    'enable_mariabackup': enable_mariabackup,
                    'database_password': db_cred,
                    'mariadb_backup_database_password': backup_db_cred,
                    'mariadb_shard_root_user_prefix': root_prefix,
                    'mariadb_shard_backup_user_prefix': backup_prefix,
                },
                'secondary1': {
                    'mariadb_shard_id': db_shards[0],
                    'enable_mariabackup': enable_mariabackup,
                    'database_password': db_cred,
                    'mariadb_backup_database_password': backup_db_cred,
                    'mariadb_shard_root_user_prefix': root_prefix,
                    'mariadb_shard_backup_user_prefix': backup_prefix,
                },
                'secondary2': {
                    'mariadb_shard_id': db_shards[1],
                    'enable_mariabackup': enable_mariabackup,
                    'database_password': db_cred,
                    'mariadb_backup_database_password': backup_db_cred,
                    'mariadb_shard_root_user_prefix': root_prefix,
                    'mariadb_shard_backup_user_prefix': backup_prefix,
                },
            },
        })

        result = {
            "shards": {
                db_shards[0]: {
                    "hosts": [
                        "primary",
                        "secondary1"
                    ]
                },
                db_shards[1]: {
                    "hosts": [
                        "secondary2"
                    ]
                }
            },
            "users": [
                {
                    "password": db_cred,
                    "shard_id": db_shards[0],
                    "user": f"{root_prefix}0"
                },
                {
                    "password": backup_db_cred,
                    "shard_id": db_shards[0],
                    "user": f"{backup_prefix}0"
                },
                {
                    "password": db_cred,
                    "shard_id": db_shards[1],
                    "user": f"{root_prefix}1"
                },
                {
                    "password": backup_db_cred,
                    "shard_id": db_shards[1],
                    "user": f"{backup_prefix}1"
                }
            ]
        }
        self.assertEqual(result, database_shards_info(context, hostnames))

    def test_valid_shards_info_without_backup_user(self):
        hostnames = ['primary', 'secondary1', 'secondary2']
        enable_mariabackup = 'no'
        root_prefix = 'root_shard_'
        db_cred = 'SECRET'
        db_shards = ['0', '1']

        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'mariadb_shard_id': db_shards[0],
                    'enable_mariabackup': enable_mariabackup,
                    'database_password': db_cred,
                    'mariadb_shard_root_user_prefix': root_prefix,
                },
                'secondary1': {
                    'mariadb_shard_id': db_shards[0],
                    'enable_mariabackup': enable_mariabackup,
                    'database_password': db_cred,
                    'mariadb_shard_root_user_prefix': root_prefix,
                },
                'secondary2': {
                    'mariadb_shard_id': db_shards[1],
                    'enable_mariabackup': enable_mariabackup,
                    'database_password': db_cred,
                    'mariadb_shard_root_user_prefix': root_prefix,
                },
            },
        })

        result = {
            "shards": {
                db_shards[0]: {
                    "hosts": [
                        "primary",
                        "secondary1"
                    ]
                },
                db_shards[1]: {
                    "hosts": [
                        "secondary2"
                    ]
                }
            },
            "users": [
                {
                    "password": db_cred,
                    "shard_id": db_shards[0],
                    "user": f"{root_prefix}0"
                },
                {
                    "password": db_cred,
                    "shard_id": db_shards[1],
                    "user": f"{root_prefix}1"
                }
            ]
        }
        self.assertEqual(result, database_shards_info(context, hostnames))

    def test_valid_shards_info_with_different_users_and_pass(self):
        hostnames = ['primary', 'secondary1', 'secondary2']
        enable_mariabackup = 'yes'
        root_prefix = 'superman_shard_'
        root_prefix_2 = 'batman_shard_'
        backup_prefix = 'backupman_shard_'
        db_cred = 'kRypTonyte'
        backup_db_cred = 'kRypTonyte1'
        db_shards = ['0', '1']

        context = self._make_context({
            'inventory_hostname': 'primary',
            'hostvars': {
                'primary': {
                    'mariadb_shard_id': db_shards[0],
                    'enable_mariabackup': enable_mariabackup,
                    'database_password': db_cred,
                    'mariadb_backup_database_password': backup_db_cred,
                    'mariadb_shard_root_user_prefix': root_prefix,
                    'mariadb_shard_backup_user_prefix': backup_prefix,
                },
                'secondary1': {
                    'mariadb_shard_id': db_shards[0],
                    'enable_mariabackup': enable_mariabackup,
                    'database_password': db_cred,
                    'mariadb_backup_database_password': backup_db_cred,
                    'mariadb_shard_root_user_prefix': root_prefix,
                    'mariadb_shard_backup_user_prefix': backup_prefix,
                },
                'secondary2': {
                    'mariadb_shard_id': db_shards[1],
                    'enable_mariabackup': 'no',
                    'database_password': db_cred,
                    'mariadb_backup_database_password': backup_db_cred,
                    'mariadb_shard_root_user_prefix': root_prefix_2,
                },
            },
        })

        result = {
            "shards": {
                db_shards[0]: {
                    "hosts": [
                        "primary",
                        "secondary1"
                    ]
                },
                db_shards[1]: {
                    "hosts": [
                        "secondary2"
                    ]
                }
            },
            "users": [
                {
                    "password": db_cred,
                    "shard_id": db_shards[0],
                    "user": f"{root_prefix}0"
                },
                {
                    "password": backup_db_cred,
                    "shard_id": db_shards[0],
                    "user": f"{backup_prefix}0"
                },
                {
                    "password": db_cred,
                    "shard_id": db_shards[1],
                    "user": f"{root_prefix_2}1"
                },
            ]
        }
        self.assertEqual(result, database_shards_info(context, hostnames))
