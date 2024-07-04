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

import sys

from cliff.app import App
from cliff.commandmanager import CommandManager

from kolla_ansible import version


class KollaAnsibleApp(App):

    def __init__(self):
        release_version = version.version_info.release_string()
        super().__init__(
            description="Kolla Ansible Command Line Interface (CLI)",
            version=release_version,
            command_manager=CommandManager("kolla_ansible.cli"),
            deferred_help=True,
        )

    def initialize_app(self, argv):
        self.LOG.debug("initialize_app")

    def prepare_to_run_command(self, cmd):
        self.LOG.debug("prepare_to_run_command %s", cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.LOG.debug("clean_up %s", cmd.__class__.__name__)
        if err:
            self.LOG.debug("got an error: %s", err)


def main(argv=sys.argv[1:]):
    myapp = KollaAnsibleApp()
    return myapp.run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
