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

"""Custom ansible-lint rule to enforce become on
   kolla_container/kolla_container_facts/kolla_toolbox modules."""

from typing import Any

from ansiblelint.errors import MatchError
from ansiblelint.file_utils import Lintable
from ansiblelint.rules import AnsibleLintRule


class KollaContainerBecomeRule(AnsibleLintRule):
    """Kolla container modules should have become set to true."""

    id = "kolla-container-become"
    description = """Kolla container module invocations should have become set
                     to true (task or block level)"""
    severity = "MEDIUM"
    tags = ["security", "kolla"]
    version_added = "v6.0.0"
    version_changed = "v6.0.0"

    def matchyaml(self, file: Lintable) -> list[MatchError]:
        """Check if Kolla container module tasks have become set to True.

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

           Checks kolla_container/kolla_container_facts/kolla_toolbox modules
           with become.

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

            # Check if this task uses Kolla container modules
            module_name = None

            # Check for Kolla modules in various formats
            kolla_modules = ['kolla_container', 'kolla_container_facts',
                             'kolla_toolbox']

            for kolla_module in kolla_modules:
                if kolla_module in task:
                    module_name = kolla_module
                    break

            # If this is a Kolla container task, check for become
            if module_name:
                if effective_become is not True:
                    task_name = task.get('name', 'unnamed task')

                    if task_become is False:
                        message = (f"Kolla container task '{task_name}' "
                                   f"(module: {module_name}) has 'become: "
                                   f"false'")
                        if parent_become is True:
                            message += """ which overrides block-level
                                           'become: true'"""
                    elif task_become is None and parent_become is False:
                        message = (f"Kolla container task '{task_name}' "
                                   f"(module: {module_name}) inherits "
                                   f"'become: false' from block")
                    elif task_become is None and parent_become is None:
                        message = (f"Kolla container task '{task_name}' "
                                   f"(module: {module_name}) is missing "
                                   f"'become: true' at task or block level")
                    else:
                        message = (f"Kolla container task '{task_name}' "
                                   f"(module: {module_name}) has 'become: "
                                   f"{task_become}' instead of 'true'")

                    errors.append(
                        self.create_matcherror(
                            message=message,
                            filename=file,
                            lineno=task.get('__line__', 1)
                        )
                    )
