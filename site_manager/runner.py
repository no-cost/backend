"""
Lower-level Ansible wrapper for tenant lifecycle management.
"""

import ansible_runner
from pathlib import Path
from typing import Any

from settings import VARS
from utils import random_string


ANSIBLE_ROOT = Path(__file__).parent.parent / "ansible"
PLAYBOOKS_ROOT = ANSIBLE_ROOT / "playbooks"


def run_playbook(
    playbook_path: str,
    tags: str | None = None,
    quiet: bool = True,
    extravars: dict[str, Any] = {},
) -> ansible_runner.Runner:
    """
    Run an Ansible playbook with the given extra variables.
    """

    all_vars = VARS.copy()
    all_vars.update(extravars)

    cmdline = "--connection=local -i localhost,"
    if tags:
        cmdline += f" --tags {tags}"
    result = ansible_runner.run(
        private_data_dir=str(ANSIBLE_ROOT),  # path must be str
        playbook=str(PLAYBOOKS_ROOT / playbook_path),
        extravars=all_vars,
        cmdline=cmdline,
        quiet=quiet,
    )

    if result.status != "successful":
        raise AnsibleError(playbook_path, result)

    return result


async def provision_tenant(
    tenant_tag: str,
    service_type: str,
    admin_email: str,
    force: bool = False,
) -> ansible_runner.Runner:
    """
    Provision a new tenant using Ansible.
    """

    return run_playbook(
        "provision/main.yml",
        {
            "tenant_tag": tenant_tag,
            "service_type": service_type,
            "tenant_admin_email": admin_email,
            "force": force,
        },
    )


async def remove_tenant(
    tenant_tag: str,
    service_type: str,
    skip_backup: bool = False,
) -> ansible_runner.Runner:
    """
    Remove a tenant using Ansible.
    """

    return run_playbook(
        "removal/main.yml",
        {
            "tenant_tag": tenant_tag,
            "service_type": service_type,
            "skip_backup": skip_backup,
        },
    )


async def backup_tenant(
    tenant_tag: str,
    service_type: str,
) -> ansible_runner.Runner:
    """
    Backup a tenant using Ansible.
    """

    return run_playbook(
        "removal/main.yml",
        tags="backup",
        extravars={
            "tenant_tag": tenant_tag,
            "service_type": service_type,
            "skip_backup": False,
        },
    )


class AnsibleError(Exception):
    """wrapper to extract failed tasks from ansible events"""

    def __init__(self, playbook_path: str, result: "ansible_runner.Runner"):
        self.playbook_path = playbook_path
        self.result = result
        self.failed_tasks = self._extract_failed_tasks(result.events)
        super().__init__(self.__str__())

    def _extract_failed_tasks(self, events: list[dict]) -> list[dict]:
        failed = []
        for event in events:
            if event.get("event") in ("runner_on_failed", "runner_on_unreachable"):
                event_data = event.get("event_data", {})
                res = event_data.get("res", {})
                failed.append({
                    "task": event_data.get("task", "unknown"),
                    "host": event_data.get("host", "unknown"),
                    "msg": res.get("msg", res.get("stderr", str(res))),
                })
        return failed

    def __str__(self) -> str:
        msg = f"Playbook {self.playbook_path} failed with status: {self.result.status}"
        if self.failed_tasks:
            task_lines = [
                f"  - Task '{t['task']}' on '{t['host']}': {t['msg']}"
                for t in self.failed_tasks
            ]
            msg += "\n\nFailed tasks:\n" + "\n".join(task_lines)
        else:
            msg += f"\n\nrc: {self.result.rc}, stats: {self.result.stats}"
        return msg
