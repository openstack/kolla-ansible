# Copyright (c) 2017 StackHPC Ltd.
#
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

import glob
import json
import logging
import os
import subprocess  # nosec
import sys
import yaml

from importlib.metadata import Distribution
from time import sleep

LOG = logging.getLogger(__name__)


def get_data_files_path(*relative_path) -> os.path:
    """Given a relative path to a data file, return the absolute path"""
    # Detect editable pip install / python setup.py develop and use a path
    # relative to the source directory
    return os.path.join(_get_base_path(), *relative_path)


def _detect_install_prefix(path: os.path) -> str:
    script_path = os.path.realpath(path)
    script_path = os.path.normpath(script_path)
    components = script_path.split(os.sep)
    # use heuristic: anything before the last 'lib' in path is the prefix
    if 'lib' not in components:
        return None
    last_lib = len(components) - 1 - components[::-1].index('lib')
    prefix = components[:last_lib]
    prefix_path = os.sep.join(prefix)
    return prefix_path


def _get_direct_url_if_editable(dist: Distribution) -> str:
    direct_url = os.path.join(dist._path, 'direct_url.json')
    editable = None
    if os.path.isfile(direct_url):
        with open(direct_url, 'r') as f:
            direct_url_content = json.loads(f.readline().strip())
            dir_info = direct_url_content.get('dir_info')
            if dir_info is not None:
                editable = dir_info.get('editable')
            if editable:
                url = direct_url_content['url']
                prefix = 'file://'
                if url.startswith(prefix):
                    return url[len(prefix):]

    return None


def _get_base_path() -> os.path:
    """Return location where kolla-ansible package is installed."""
    override = os.environ.get("KOLLA_ANSIBLE_DATA_FILES_PATH")
    if override:
        return os.path.join(override)

    kolla_ansible_dist = list(Distribution.discover(name="kolla_ansible"))
    if kolla_ansible_dist:
        direct_url = _get_direct_url_if_editable(kolla_ansible_dist[0])
        if direct_url:
            return direct_url

    egg_glob = os.path.join(
        sys.prefix, 'lib*', 'python*', '*-packages', 'kolla-ansible.egg-link'
    )
    egg_link = glob.glob(egg_glob)
    if egg_link:
        with open(egg_link[0], "r") as f:
            realpath = f.readline().strip()
        return os.path.join(realpath)

    prefix = _detect_install_prefix(__file__)
    if prefix:
        return os.path.join(prefix, "share", "kolla-ansible")

    # Assume uninstalled
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")


def galaxy_collection_install(requirements_file: str,
                              collections_path: str = None,
                              force: bool = False) -> None:
    """Install ansible collections needed by kolla-ansible roles."""
    requirements = read_yaml_file(requirements_file)
    if not isinstance(requirements, dict):
        # Handle legacy role list format, which causes the command to fail.
        return
    args = ["collection", "install"]
    if collections_path:
        args += ["--collections-path", collections_path]
    args += ["--requirements-file", requirements_file]
    if force:
        args += ["--force"]

    for retry_count in range(1, 6):
        try:
            run_command("ansible-galaxy", args)
        except subprocess.CalledProcessError as e:
            if retry_count < 5:
                LOG.warning(f"Failed to install Ansible collections from "
                            f"{requirements_file} using Ansible Galaxy "
                            f"(error: {e}) (retry: {retry_count}/5)")
                sleep(2)
                continue
            else:
                LOG.error(f"Failed to install Ansible collections from "
                          f"{requirements_file} using Ansible Galaxy "
                          f"(error: {e}) after 5 retries")
                LOG.error("Exiting")
                sys.exit(e.returncode)
        break


def read_file(path: os.path, mode: str = "r") -> str | bytes:
    """Read the content of a file."""
    with open(path, mode) as f:
        return f.read()


def read_yaml_file(path: os.path):
    """Read and decode a YAML file."""
    try:
        content = read_file(path)
    except IOError as e:
        print("Failed to open YAML file %s: %s" %
              (path, repr(e)))
        sys.exit(1)
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        print("Failed to decode YAML file %s: %s" %
              (path, repr(e)))
        sys.exit(1)


def is_readable_dir(path: os.path) -> bool:
    """Check whether a path references a readable directory."""
    if not os.path.exists(path):
        return {"result": False, "message": "Path does not exist"}
    if not os.path.isdir(path):
        return {"result": False, "message": "Path is not a directory"}
    if not os.access(path, os.R_OK):
        return {"result": False, "message": "Directory is not readable"}
    return {"result": True}


def is_readable_file(path: os.path) -> bool:
    """Check whether a path references a readable file."""
    if not os.path.exists(path):
        return {"result": False, "message": "Path does not exist"}
    if not os.path.isfile(path):
        return {"result": False, "message": "Path is not a file"}
    if not os.access(path, os.R_OK):
        return {"result": False, "message": "File is not readable"}
    return {"result": True}


def run_command(executable: str,
                args: list,
                quiet: bool = False,
                **kwargs) -> None:
    """Run a command, checking the output.

    :param quiet: Redirect output to /dev/null
    """
    full_cmd = [executable] + args
    cmd_string = " ".join(full_cmd)
    LOG.debug("Running command: %s", cmd_string)

    if quiet:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
        subprocess.run(full_cmd, check=True, shell=False, **kwargs)  # nosec
    else:
        subprocess.run(full_cmd, check=True, shell=False, **kwargs)  # nosec
