"""
Lower-level Ansible wrapper for tenant lifecycle management.
"""

from os import environ
from pathlib import Path
from typing import Any

import ansible_runner

from settings import VARS

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
    all_vars["ansible_connection"] = "local"

    cmdline = f"--tags {tags}" if tags else ""
    # paths must be str
    result = ansible_runner.run(
        private_data_dir=str(ANSIBLE_ROOT),
        project_dir=str(PLAYBOOKS_ROOT),
        playbook=playbook_path,  # relative to project_dir
        inventory="localhost,",
        extravars=all_vars,
        envvars={"PATH": environ["PATH"]},
        cmdline=cmdline,
        quiet=quiet,
    )

    if result.status != "successful":
        raise RuntimeError(
            f"Playbook {playbook_path} failed with status: {result.status}. rc: {result.rc}, stats: {result.stats}.\n\nstdout: {result.stdout.read()}\nstderr: {result.stderr.read()}"
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
