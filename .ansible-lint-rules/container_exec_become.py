# Copyright 2026 Michal Nasiadka
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

"""Custom ansible-lint rule to enforce become on container exec commands."""

from typing import Any

from ansiblelint.errors import MatchError
from ansiblelint.file_utils import Lintable
from ansiblelint.rules import AnsibleLintRule


class ContainerExecBecomeRule(AnsibleLintRule):

    id = "container-exec-become"
    description = """shell/command tasks starting with 'docker exec' or
                     'podman exec' should have become set to True"""
    severity = "MEDIUM"
    tags = ["security", "container"]
    version_added = "v6.0.0"
    version_changed = "v6.0.0"

    def matchyaml(self, file: Lintable) -> list[MatchError]:
        """Check if container exec commands have become set to True.

        Args:
            file: The file being linted

        Returns:
            List of MatchError objects if violations found
        """
        errors = []

        # Get the parsed YAML data
        data = file.data
        if not data:
            return errors

        # Process plays or task files
        if isinstance(data, list):
            # Check if this is a playbook (contains plays) or
            # a task file (just tasks)
            if data and isinstance(data[0], dict):
                # If first item has 'hosts' or 'import_playbook',
                # it's a playbook
                first_item = data[0]
                if 'hosts' in first_item or 'import_playbook' in first_item:
                    # Process as playbook
                    for play_idx, play in enumerate(data):
                        if not isinstance(play, dict):
                            continue

                        # Check tasks at play level
                        self._check_tasks(play.get('tasks', []), None, errors,
                                          file, f".[{play_idx}].tasks")

                        # Check pre_tasks
                        self._check_tasks(play.get('pre_tasks', []), None,
                                          errors, file,
                                          f".[{play_idx}].pre_tasks")

                        # Check post_tasks
                        self._check_tasks(play.get('post_tasks', []), None,
                                          errors, file,
                                          f".[{play_idx}].post_tasks")

                        # Check handlers
                        self._check_tasks(play.get('handlers', []), None,
                                          errors, file,
                                          f".[{play_idx}].handlers")
                else:
                    # Process as task file (list of tasks directly)
                    self._check_tasks(data, None, errors, file, ".")

        return errors

    def _check_tasks(
        self,
        tasks: list[dict[str, Any]],
        parent_become: bool | None,
        errors: list[MatchError],
        file: Lintable,
        path: str
    ) -> None:
        """Recursively check tasks and blocks.

           Check for container exec commands with become.

        Args:
            tasks: List of tasks to check
            parent_become: The become value inherited from parent block
            errors: List to append errors to
            file: The file being linted
            path: Current path in the YAML structure
        """
        if not tasks:
            return

        for task_idx, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue

            task_path = f"{path}[{task_idx}]"

            # Determine effective become value for this task
            task_become = task.get('become')
            if task_become is not None:
                effective_become = task_become
            else:
                effective_become = parent_become

            # Check if this is a block
            if 'block' in task:
                # For blocks, pass down the effective become value
                block_become = task.get('become')
                if block_become is not None:
                    inherited_become = block_become
                else:
                    inherited_become = parent_become

                # Recursively check tasks in the block
                self._check_tasks(
                    task.get('block', []),
                    inherited_become,
                    errors,
                    file,
                    f"{task_path}.block"
                )

                # Also check rescue and always sections
                if 'rescue' in task:
                    self._check_tasks(
                        task.get('rescue', []),
                        inherited_become,
                        errors,
                        file,
                        f"{task_path}.rescue"
                    )

                if 'always' in task:
                    self._check_tasks(
                        task.get('always', []),
                        inherited_become,
                        errors,
                        file,
                        f"{task_path}.always"
                    )

                continue

            # Check if this task uses shell or command module
            module_name = None
            command_value = None

            # Check for shell/command modules
            shell_modules = [
                'ansible.builtin.shell', 'shell',
                'ansible.builtin.command', 'command'
            ]

            for shell_module in shell_modules:
                if shell_module in task:
                    module_name = shell_module
                    # Get the command - can be a string or dict
                    cmd = task[shell_module]
                    if isinstance(cmd, str):
                        command_value = cmd
                    elif isinstance(cmd, dict):
                        # Command might be in 'cmd' key or the module args
                        command_value = (cmd.get('cmd') or
                                         cmd.get('_raw_params'))
                    break

            # If this is a shell/command task, check if it starts with
            # docker/podman exec
            if module_name and command_value:
                # Strip leading whitespace and newlines, check if it starts
                # with docker/podman exec
                cmd_stripped = command_value.strip()

                # Check for hardcoded docker/podman exec (should use variable)
                uses_hardcoded_exec = (
                    cmd_stripped.startswith('docker exec') or
                    cmd_stripped.startswith('podman exec')
                )

                if uses_hardcoded_exec:
                    # Flag hardcoded container engine usage
                    task_name = task.get('name', 'unnamed task')
                    if cmd_stripped.startswith('docker exec'):
                        exec_type = 'docker exec'
                    else:
                        exec_type = 'podman exec'

                    message = (f"Task '{task_name}' uses hardcoded "
                               f"'{exec_type}' - use "
                               f"'{{{{ kolla_container_engine }}}} exec' "
                               f"instead")

                    errors.append(
                        self.create_matcherror(
                            message=message,
                            filename=file,
                            lineno=task.get('__line__', 1)
                        )
                    )
                    # Continue to also check become requirement

                # Check for variable-based container engine followed by exec
                # e.g., "{{ kolla_container_engine }} exec",
                # "{{ container_engine }} exec"
                import re
                variable_exec_pattern = r'^\{\{[^}]+\}\}\s+exec\s+'
                uses_variable_exec = re.match(variable_exec_pattern,
                                              cmd_stripped)

                is_container_exec = uses_hardcoded_exec or uses_variable_exec

                if is_container_exec:
                    # Check if become is True
                    if effective_become is not True:
                        task_name = task.get('name', 'unnamed task')

                        # Determine exec type for error message
                        if cmd_stripped.startswith('docker exec'):
                            exec_type = 'docker exec'
                        elif cmd_stripped.startswith('podman exec'):
                            exec_type = 'podman exec'
                        else:
                            exec_type = 'container exec (via variable)'

                        if task_become is False:
                            message = (f"Task '{task_name}' uses "
                                       f"'{exec_type}' but has "
                                       f"'become: false'")
                            if parent_become is True:
                                message += """ which overrides block-level
                                                'become: true'"""
                        elif task_become is None and parent_become is False:
                            message = (f"Task '{task_name}' uses "
                                       f"'{exec_type}' and inherits "
                                       f"'become: false' from block")
                        elif task_become is None and parent_become is None:
                            message = (f"Task '{task_name}' uses "
                                       f"'{exec_type}' but is missing "
                                       f"'become: true' at task or "
                                       f"block level")
                        else:
                            message = (f"Task '{task_name}' uses "
                                       f"'{exec_type}' but has "
                                       f"'become: {task_become}' instead of "
                                       f"'true'")

                        errors.append(
                            self.create_matcherror(
                                message=message,
                                filename=file,
                                lineno=task.get('__line__', 1)
                            )
                        )
