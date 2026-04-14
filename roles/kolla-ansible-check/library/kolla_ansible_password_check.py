#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2026 StackHPC Ltd.
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

from ansible.module_utils.basic import AnsibleModule
import atexit
import os
import subprocess
import tempfile

__metaclass__ = type

DOCUMENTATION = r"""
---
module: kolla_ansible_password_check
short_description: Check kolla-ansible passwords.yml for leaked secrets
description:
  - Reads a kolla-ansible passwords.yml file and searches the systemd journal
    for any occurrences of the password values.
  - Reports which variable names had their secrets found in the journal.
  - Fails if any leaked secrets are detected.
  - All secret values are handled internally and never appear in Ansible
    output, logs, or return values — only variable names are ever surfaced.
version_added: "1.0.0"
author:
  - Michal Nasiadka <mnasiadka@gmail.com>
options:
  passwords_file:
    description:
      - Path to the kolla-ansible passwords.yml file on the remote host.
    type: path
    required: true
  min_password_length:
    description:
      - Minimum length a password value must have to be checked.
      - Very short values (e.g. single characters) are skipped to avoid
        false positives.
    type: int
    default: 8
  journalctl_args:
    description:
      - Extra arguments passed verbatim to journalctl
        (e.g. C(--since "1 hour ago")).
      - Do not include C(--no-pager) or C(-g) / C(--grep) as these are added
        automatically.
    type: str
    default: ""
  fail_on_leaked:
    description:
      - Whether to fail the task when leaked secrets are found.
      - Set to C(false) to report leaks without failing, useful for dry-runs.
    type: bool
    default: true
  return_stdout:
    description:
      - When C(true), include the journalctl output for each leaked entry
        in the C(leaked_entries) return value.
      - Has no effect when there are no leaks.
      - Note that journalctl output for a leaked entry will contain the
        secret value. Use C(no_log) on any subsequent tasks that display
        C(leaked_entries) if you need to protect it.
    type: bool
    default: false
  ignore_keys:
    description:
      - List of variable names whose presence in the journal should not be
        treated as a leak.
      - Entries in this list are still checked against the journal; they are
        just excluded from C(leaked_keys), C(leaked_entries), and the failure
        condition.
      - Matched entries are reported separately in C(ignored_leaked_keys) so
        there is a full audit trail of what was intentionally allowed.
    type: list
    elements: str
    default: []
notes:
  - Requires C(journalctl) and C(grep) to be available on the remote host.
  - Must be run with sufficient privileges to read the journal
    (typically requires C(become: true)).
  - The journal is dumped once to a temporary file and then C(grep -F) is
    run per password against that file, which is significantly faster than
    running C(journalctl --grep) once per password.
  - The temporary file is deleted automatically when the module exits.
  - Secret values are B(never) included in module return data, only variable
    names are returned, making this safe to use without C(no_log).
requirements:
  - journalctl (systemd)
  - PyYAML
"""

EXAMPLES = r"""
- name: Check kolla passwords for journal leaks
  kolla_ansible_password_check:
    passwords_file: /etc/kolla/passwords.yml
  become: true
  register: leak_result

- name: Show which keys leaked
  ansible.builtin.debug:
    msg: "Leaked keys: {{ leak_result.leaked_keys }}"
  when: leak_result.leaked_keys | length > 0

# Non-failing variant for reporting
- name: Audit journal leaks without failing
  kolla_ansible_password_check:
    passwords_file: /etc/kolla/passwords.yml
    fail_on_leaked: false
    journalctl_args: '--since "24 hours ago"'
  become: true
  register: audit_result
"""

RETURN = r"""
leaked_keys:
  description:
    - List of variable names from passwords.yml whose values were found in
      the journal. Never contains the actual secret values.
  type: list
  elements: str
  returned: always
  sample: ["keystone_db_password", "nova_keystone_password"]
checked_count:
  description: Number of password entries that were actually checked.
  type: int
  returned: always
  sample: 42
skipped_count:
  description:
    - Number of entries skipped because their value was empty, null,
      non-string, or shorter than min_password_length.
  type: int
  returned: always
  sample: 5
msg:
  description: Human-readable summary of the check result.
  type: str
  returned: always
  sample: "No secrets found in journal. Checked 42 entries."
leaked_entries:
  description:
    - Mapping of leaked variable names to their journalctl output.
    - Only populated when C(return_stdout: true) and leaks are found.
    - The journalctl output will contain the secret value — treat accordingly.
  type: dict
  returned: when return_stdout is true and leaks are found
  sample: {"keystone_db_password": "Mar 26 ... keystone_db_password=s3cr3t"}
ignored_leaked_keys:
  description:
    - List of variable names that were found in the journal but are present
      in C(ignore_keys) and therefore excluded from C(leaked_keys).
    - Always returned so there is a full audit trail of intentional allowances.
  type: list
  elements: str
  returned: always
  sample: ["deployment_ssh_key"]
"""

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_passwords(module, passwords_file):
    """Load and parse the kolla passwords YAML file.

    Returns a dict of {variable_name: password_value}.
    Aborts the module on any read/parse error.
    """
    if not os.path.isfile(passwords_file):
        module.fail_json(
            msg="passwords_file not found: {}".format(passwords_file))

    try:
        with open(passwords_file, "r") as fh:
            content = fh.read()
    except OSError as exc:
        module.fail_json(
            msg="Cannot read passwords_file: {}".format(str(exc)))

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        module.fail_json(
            msg="Failed to parse passwords YAML: {}".format(str(exc)))

    if data is None:
        return {}
    if not isinstance(data, dict):
        module.fail_json(
            msg="passwords_file must contain a YAML mapping at the top level"
        )

    return data


def dump_journal(module, extra_args):
    """Dump the full journal to a temporary file.

    Returns the path to the temp file. The file is registered for deletion
    via atexit so it is cleaned up even if the module exits unexpectedly.
    """
    try:
        tmp = tempfile.NamedTemporaryFile(
            prefix="kolla_password_check_",
            suffix=".log",
            delete=False,
        )
        tmp.close()
    except OSError as exc:
        module.fail_json(msg="Failed to create temp file: {}".format(str(exc)))

    # Register cleanup before the subprocess so the file is always removed.
    atexit.register(_unlink_silent, tmp.name)

    cmd = ["journalctl", "--no-pager"]
    if extra_args:
        cmd.extend(extra_args.split())

    try:
        with open(tmp.name, "w") as fh:
            result = subprocess.run(
                cmd,
                stdout=fh,
                stderr=subprocess.PIPE,
            )
    except OSError as exc:
        module.fail_json(msg="Failed to run journalctl: {}".format(str(exc)))

    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        module.fail_json(
            msg="journalctl exited with code {}: {}".format(
                result.returncode, stderr_text
            )
        )

    return tmp.name


def grep_journal(module, journal_file, value, return_stdout):
    """Search journal_file for value using grep -F (fixed string).

    Returns (found, matching_lines) where matching_lines is a string of
    all matching lines (only populated when return_stdout is True).
    """
    # -F: fixed string (no regex, no escaping needed)
    # -q: quiet — exit 0 immediately on first match when return_stdout is False
    cmd = ["grep", "-F"]
    if not return_stdout:
        cmd.append("-q")
    cmd.extend(["--", value, journal_file])

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        module.fail_json(msg="Failed to run grep: {}".format(str(exc)))

    # grep exits 0 = match found, 1 = no match, 2+ = error.
    if result.returncode == 0:
        stdout = result.stdout.decode(
            "utf-8", errors="replace") if return_stdout else ""
        return True, stdout
    elif result.returncode == 1:
        return False, ""
    else:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        module.warn(
            "grep returned exit code {} while checking an entry. "
            "stderr: {}".format(result.returncode, stderr_text)
        )
        return False, ""


def _unlink_silent(path):
    """Delete a file, ignoring errors (used as atexit handler)."""
    try:
        os.unlink(path)
    except OSError:
        pass


def run_module():
    module_args = dict(
        passwords_file=dict(type="path", required=True),
        min_password_length=dict(type="int", default=8),
        journalctl_args=dict(type="str", default=""),
        fail_on_leaked=dict(type="bool", default=True),
        return_stdout=dict(type="bool", default=False),
        ignore_keys=dict(type="list", elements="str", default=[]),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    if not HAS_YAML:
        module.fail_json(msg="PyYAML is required for this module.")

    passwords_file = module.params["passwords_file"]
    min_length = module.params["min_password_length"]
    extra_args = module.params["journalctl_args"]
    fail_on_leaked = module.params["fail_on_leaked"]
    return_stdout = module.params["return_stdout"]
    ignore_keys = set(module.params["ignore_keys"])

    passwords = load_passwords(module, passwords_file)

    leaked_keys = []
    leaked_entries = {}
    ignored_leaked_keys = []
    checked_count = 0
    skipped_count = 0

    if not module.check_mode:
        journal_file = dump_journal(module, extra_args)

    for idx, (key, value) in enumerate(passwords.items()):
        # Skip null, non-string, or suspiciously short values.
        if not isinstance(value, str):
            skipped_count += 1
            continue
        if len(value) < min_length:
            skipped_count += 1
            continue

        checked_count += 1

        # In check mode we report what *would* be checked without hitting
        # journalctl, since we can't know what the journal contains.
        if module.check_mode:
            continue

        found, stdout = grep_journal(
            module, journal_file, value, return_stdout)
        if found:
            if key in ignore_keys:
                # Found in journal but explicitly allowed — track separately
                # for audit purposes but do not treat as a failure.
                ignored_leaked_keys.append(key)
            else:
                # Only the key name is stored by default — the secret value is
                # intentionally never written to any Ansible data structure
                # unless return_stdout is explicitly requested.
                leaked_keys.append(key)
                if return_stdout:
                    leaked_entries[key] = stdout

    if leaked_keys:
        summary = (
            "Leaked secrets found in journal for {} variable(s): {}. "
            "Checked {} entries, skipped {}.".format(
                len(leaked_keys),
                ", ".join(leaked_keys),
                checked_count,
                skipped_count,
            )
        )
    else:
        summary = (
            "No secrets found in journal. "
            "Checked {} entries, skipped {}.""".format(
                checked_count,
                skipped_count
            )
        )

    if ignored_leaked_keys:
        summary += " Ignored {} allowed variable(s): {}.".format(
            len(ignored_leaked_keys), ", ".join(ignored_leaked_keys)
        )

    result = dict(
        changed=False,
        leaked_keys=leaked_keys,
        leaked_entries=leaked_entries,
        ignored_leaked_keys=ignored_leaked_keys,
        checked_count=checked_count,
        skipped_count=skipped_count,
        msg=summary,
    )

    if leaked_keys and fail_on_leaked:
        module.fail_json(**result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
