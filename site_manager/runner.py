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
        private_data_dir=ANSIBLE_ROOT,
        playbook=PLAYBOOKS_ROOT / playbook_path,
        extravars=all_vars,
        cmdline=cmdline,
        quiet=quiet,
    )

    if result.status != "successful":
        raise AnsibleError(
            f"Playbook {playbook_path} failed with status: {result.status}",
            status=result.status,
            rc=result.rc,
            stats=result.stats,
        )

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
    """Raised when an Ansible playbook fails."""
