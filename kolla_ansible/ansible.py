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

import logging
import os
import subprocess  # nosec
import sys

from kolla_ansible import utils
from typing import List
from typing import Tuple


DEFAULT_CONFIG_PATH = "/etc/kolla"

CONFIG_PATH_ENV = "KOLLA_CONFIG_PATH"

LOG = logging.getLogger(__name__)


def add_ansible_args(parser):
    """Add arguments required for running Ansible playbooks to a parser."""
    parser.add_argument(
        "-b",
        "--become",
        action="store_true",
        help="run operations with become (nopasswd implied)",
    )
    parser.add_argument(
        "-C",
        "--check",
        action="store_true",
        help="don't make any changes; instead, try to predict "
        "some of the changes that may occur",
    )
    parser.add_argument(
        "-D",
        "--diff",
        action="store_true",
        help="when changing (small) files and templates, show "
        "the differences in those files; works great "
        "with --check",
    )
    parser.add_argument(
        "-e",
        "--extra-vars",
        metavar="EXTRA_VARS",
        action="append",
        help="set additional variables as key=value or "
        "YAML/JSON",
    )
    parser.add_argument(
        "-i",
        "--inventory",
        metavar="INVENTORY",
        action="append",
        help="specify inventory host path ",
    )
    parser.add_argument(
        "-l",
        "--limit",
        metavar="SUBSET",
        help="further limit selected hosts to an additional "
        "pattern",
    )
    parser.add_argument(
        "--skip-tags",
        metavar="TAGS",
        help="only run plays and tasks whose tags do not "
        "match these values",
    )
    parser.add_argument(
        "-t",
        "--tags",
        metavar="TAGS",
        help="only run plays and tasks tagged with these "
        "values",
    )
    parser.add_argument(
        "-lt",
        "--list-tasks",
        action="store_true",
        help="only print names of tasks, don't run them, "
        "note this has no affect on kolla-ansible.",
    )
    parser.add_argument(
        "-p", "--playbook",
        metavar="PLAYBOOKS",
        action="append",
        help="Specify custom playbooks for kolla ansible "
        "to use"
    ),
    parser.add_argument(
        "--vault-id",
        metavar="VAULT_IDS",
        action="append",
        help="the vault identity to use. "
             "This argument may be specified multiple times.",
        default=[]
    ),
    parser.add_argument(
        "--vault-password-file",
        "--vault-pass-file",
        metavar="VAULT_PASSWORD_FILES",
        action="append",
        help="vault password file",
        default=[]
    ),
    parser.add_argument(
        "-J",
        "--ask-vault-password",
        "--ask-vault-pass",
        action="store_true",
        help="ask for vault password"
    )


def add_kolla_ansible_args(parser):
    """Add arguments required for running Kolla Ansible to a parser."""
    default_config_path = os.getenv(CONFIG_PATH_ENV, DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--configdir",
        default=default_config_path,
        dest="kolla_config_path",
        help="path to Kolla configuration."
        "(default=$%s or %s)" % (CONFIG_PATH_ENV, DEFAULT_CONFIG_PATH),
    )
    parser.add_argument(
        "--passwords",
        dest="kolla_passwords",
        help="Path to the kolla ansible passwords file"
    )


def _get_inventory_paths(parsed_args) -> List[str]:
    """Return path to the Kolla Ansible inventory."""
    if parsed_args.inventory:
        return parsed_args.inventory

    default_inventory = os.path.join(
        os.path.abspath(parsed_args.kolla_config_path),
        "ansible", "inventory", "all-in-one")
    return [default_inventory]


def _validate_args(parsed_args, playbooks: list) -> None:
    """Validate Kolla Ansible arguments."""
    result = utils.is_readable_dir(
        os.path.abspath(parsed_args.kolla_config_path))
    if not result["result"]:
        LOG.error(
            "Kolla Ansible configuration path %s is invalid: %s",
            os.path.abspath(parsed_args.kolla_config_path),
            result["message"],
        )
        sys.exit(1)

    inventories = _get_inventory_paths(parsed_args)
    for inventory in inventories:
        result = utils.is_readable_dir(inventory)
        if not result["result"]:
            # NOTE(mgoddard): Previously the inventory was a file, now it is a
            # directory to allow us to support inventory host_vars. Support
            # both formats for now.
            result_f = utils.is_readable_file(inventory)
            if not result_f["result"]:
                LOG.error(
                    "Kolla inventory %s is invalid: %s",
                    inventory, result["message"]
                )
                sys.exit(1)

    for playbook in playbooks:
        result = utils.is_readable_file(playbook)
        if not result["result"]:
            LOG.error(
                "Kolla Ansible playbook %s is invalid: %s",
                playbook, result["message"]
            )
            sys.exit(1)

    if parsed_args.kolla_passwords:
        passwd_file = parsed_args.kolla_passwords
    else:
        passwd_file = os.path.join(
            os.path.abspath(parsed_args.kolla_config_path), "passwords.yml")
    result = utils.is_readable_file(passwd_file)
    if not result["result"]:
        LOG.error("Kolla Ansible passwords file %s is invalid: %s",
                  passwd_file, result["message"])

    globals_file = os.path.join(os.path.abspath(
        os.path.abspath(parsed_args.kolla_config_path)), "globals.yml")
    result = utils.is_readable_file(globals_file)
    if not result["result"]:
        LOG.error("Kolla ansible globals file %s is invalid %s",
                  globals_file, result["message"])


def _get_vars_files(config_path: os.path) -> List[str]:
    """Return a list of Kolla Ansible configuration variable files.

    The globals.d directory in config path is searched to create the list of
    variable files. The files will be sorted alphabetically by name for each
    file, but ordering of file is kept to allow overrides.
    """
    vars_path = os.path.join(config_path, "globals.d")
    result = utils.is_readable_dir(vars_path)
    if not result["result"]:
        return []

    vars_files = []
    for vars_file in os.listdir(vars_path):
        abs_path = os.path.join(vars_path, vars_file)
        if utils.is_readable_file(abs_path)["result"]:
            root, ext = os.path.splitext(vars_file)
            if ext in (".yml", ".yaml", ".json"):
                vars_files.append(abs_path)

    return sorted(vars_files)


def build_args(parsed_args,
               playbooks: list,
               extra_vars: dict = {},
               verbose_level: int = None) -> Tuple[str, List[str]]:
    """Build arguments required for running Ansible playbooks."""
    args = list()
    if verbose_level:
        args += ["-" + "v" * verbose_level]
    if parsed_args.list_tasks:
        args += ["--list-tasks"]
    inventories = _get_inventory_paths(parsed_args)
    for inventory in inventories:
        args += ["--inventory", inventory]
    args += ["-e", "@%s" % os.path.join(
        os.path.abspath(parsed_args.kolla_config_path),
        "globals.yml")]
    args += ["-e", "@%s" % os.path.join(
        os.path.abspath(parsed_args.kolla_config_path),
        "passwords.yml")]
    for vault_id in parsed_args.vault_id:
        args += ["--vault-id", vault_id]
    for vault_pass_file in parsed_args.vault_password_file:
        args += ["--vault-password-file", vault_pass_file]
    if parsed_args.ask_vault_password:
        args += ["--ask-vault-password"]
    vars_files = _get_vars_files(
        os.path.abspath(parsed_args.kolla_config_path))
    for vars_file in vars_files:
        args += ["-e", "@%s" % vars_file]
    if parsed_args.extra_vars:
        for extra_var in parsed_args.extra_vars:
            args += ["-e", extra_var]
    if extra_vars:
        for extra_var_name, extra_var_value in extra_vars.items():
            args += ["-e", "%s=%s" % (extra_var_name, extra_var_value)]
    args += ["-e", "CONFIG_DIR=%s" %
             os.path.abspath(parsed_args.kolla_config_path)]
    if parsed_args.become:
        args += ["--become"]
    if parsed_args.check:
        args += ["--check"]
    if parsed_args.diff:
        args += ["--diff"]
    if parsed_args.limit:
        args += ["--limit", parsed_args.limit]
    if parsed_args.skip_tags:
        args += ["--skip-tags", parsed_args.skip_tags]
    if parsed_args.tags:
        args += ["--tags", parsed_args.tags]
    args += [" ".join(playbooks)]
    return ("ansible-playbook", args)


def run_playbooks(parsed_args, playbooks: list, extra_vars: dict = {},
                  quiet: bool = False, verbose_level: int = 0) -> None:
    """Run a Kolla Ansible playbook."""
    LOG.debug("Parsed arguments: %s" % parsed_args)
    _validate_args(parsed_args, playbooks)
    (executable, args) = build_args(
        parsed_args,
        playbooks,
        extra_vars=extra_vars,
        verbose_level=verbose_level,
    )

    try:
        utils.run_command(executable, args, quiet=quiet)
    except subprocess.CalledProcessError as e:
        LOG.error(
            "Kolla Ansible playbook(s) %s exited %d", ", ".join(
                playbooks), e.returncode
        )
        sys.exit(e.returncode)


def install_galaxy_collections(force: bool = True) -> None:
    """Install Ansible Galaxy collection dependencies.

    Installs collection dependencies specified in kolla-ansible,
    and if present, in kolla-ansibnle configuration.

    :param force: Whether to force reinstallation of roles.
    """
    requirements = utils.get_data_files_path("requirements.yml")
    requirements_core = utils.get_data_files_path("requirements-core.yml")
    utils.galaxy_collection_install(requirements, force=force)
    utils.galaxy_collection_install(requirements_core, force=force)
