"""
Lower-level Ansible wrapper for tenant lifecycle management.
"""

from os import environ
from pathlib import Path
from typing import Any

from ansible_runner import Runner, RunnerConfig

from settings import VARS, VENV_DIR

ANSIBLE_ROOT = Path(__file__).parent.parent / "ansible"


def run_playbook(
    playbook_path: str,
    tags: str | None = None,
    quiet: bool = True,
    extravars: dict[str, Any] = {},
) -> Runner:
    """
    Run an Ansible playbook with the given extra variables.
    """

    all_vars = VARS.copy()
    all_vars.update(extravars)
    all_vars["ansible_local_tmp"] = "/tmp/.ansible/tmp"
    all_vars["ansible_python_interpreter"] = f"{VENV_DIR}/bin/python"

    rc = RunnerConfig(
        private_data_dir=str(ANSIBLE_ROOT),
        playbook=playbook_path,  # relative to project dir: ansible/project/
        extravars=all_vars,
        envvars=dict[str, str](environ),
        tags=tags,
        quiet=quiet,
    )
    rc.prepare()

    runner = Runner(config=rc)
    runner.run()
    if runner.status != "successful":
        raise RuntimeError(
            f"Playbook {playbook_path} failed with status: {runner.status}. rc: {runner.rc}, stats: {runner.stats}.\n\nstdout: {runner.stdout.read()}\nstderr: {runner.stderr.read()}"
        )

    return runner


async def provision_tenant(
    tenant_tag: str,
    service_type: str,
    admin_email: str,
    force: bool = False,
) -> Runner:
    """
    Provision a new tenant using Ansible.
    """

    return run_playbook(
        "provision_main.yml",
        extravars={
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
) -> Runner:
    """
    Remove a tenant using Ansible.
    """

    return run_playbook(
        "removal_main.yml",
        extravars={
            "tenant_tag": tenant_tag,
            "service_type": service_type,
            "skip_backup": skip_backup,
        },
    )


async def backup_tenant(
    tenant_tag: str,
    service_type: str,
) -> Runner:
    """
    Backup a tenant using Ansible.
    """

    return run_playbook(
        "removal_main.yml",
        tags="backup",
        extravars={
            "tenant_tag": tenant_tag,
            "service_type": service_type,
            "skip_backup": False,
        },
    )
