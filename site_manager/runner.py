"""
Lower-level Ansible wrapper for tenant lifecycle management.
"""

from os import environ
from pathlib import Path
from typing import Any

from ansible_runner import Runner, RunnerConfig

from settings import VARS

ANSIBLE_ROOT = Path(__file__).parent.parent / "ansible"


def run_playbook(
    playbook_path: str,
    tags: str | None = None,
    quiet: bool = True,
    extravars: dict[str, Any] = {},
) -> Runner:
    all_vars = VARS.copy()
    all_vars.update(extravars)

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


def provision_tenant(
    tenant_tag: str,
    service_type: str,
    hostname: str,
    admin_email: str,
    reset_token: str,
    force: bool = False,
    send_email: bool = True,
) -> Runner:
    """Provision a new tenant using Ansible."""

    return run_playbook(
        "provision_main.yml",
        tags="send-email" if send_email else None,
        extravars={
            "tenant_tag": tenant_tag,
            "tenant_hostname": hostname,
            "service_type": service_type,
            "tenant_admin_email": admin_email,
            "tenant_reset_token": reset_token,
            "force": force,
        },
    )


def remove_tenant(
    tenant_tag: str,
    service_type: str,
    skip_backup: bool = False,
    send_email: bool = True,
    admin_email: str | None = None,
    hostname: str | None = None,
    reason: str | None = None,
) -> Runner:
    """Remove a tenant using Ansible."""

    return run_playbook(
        "backup_main.yml",
        extravars={
            "tenant_tag": tenant_tag,
            "service_type": service_type,
            "skip_backup": skip_backup,
            "send_email": send_email,
            "tenant_admin_email": admin_email or "",
            "tenant_hostname": hostname or "",
            "removal_reason": reason or "",
        },
    )


def backup_tenant(
    tenant_tag: str,
    service_type: str,
    periodic: bool = False,
    delete_older_than_days: int = 7,
) -> Runner:
    """Backup a tenant using Ansible."""

    return run_playbook(
        "backup_main.yml",
        tags="periodic" if periodic else "backup",
        extravars={
            "tenant_tag": tenant_tag,
            "service_type": service_type,
            "skip_backup": False,
            "delete_older_than_days": delete_older_than_days,
        },
    )


def restore_tenant(
    tenant_tag: str,
    service_type: str,
    backup_mode: str = "attic",
    backup_date: str | None = None,
) -> Runner:
    """Restore a tenant from backup."""

    extravars: dict[str, Any] = {
        "tenant_tag": tenant_tag,
        "service_type": service_type,
    }
    if backup_date:
        extravars["backup_date"] = backup_date

    return run_playbook(
        "restore_main.yml",
        tags=backup_mode,
        extravars=extravars,
    )
