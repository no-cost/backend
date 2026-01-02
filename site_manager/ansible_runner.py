"""
Ansible-runner wrapper for tenant lifecycle management.
"""

import os
from pathlib import Path
from typing import Any

import ansible_runner


ANSIBLE_ROOT = Path(__file__).parent.parent / "ansible"
PLAYBOOKS_ROOT = ANSIBLE_ROOT / "playbooks"


def get_env_vars() -> dict[str, Any]:
    """
    Get configuration variables from environment.

    Returns a dict that can be merged with extravars for Ansible.
    """

    allowed_domains = os.environ.get(
        "ALLOWED_DOMAINS", "no-cost.site,no-cost.forum,no-cost.wiki"
    ).split(",")

    return {
        "allowed_domains": allowed_domains,
        "main_domain": allowed_domains[0],
        "php_version": os.environ.get("PHP_VERSION", "8.5"),
        "paths": {
            "tenants": {
                "root": os.environ.get("TENANTS_ROOT", "/srv/host"),
                "skeleton_root": os.environ.get("SKELETON_ROOT", "/srv/skeleton"),
            },
            "backup_root": os.environ.get("BACKUP_ROOT", "/backup"),
            "backup_attic_root": os.environ.get("BACKUP_ATTIC_ROOT", "/backup/attic"),
        },
    }


def run_playbook(
    playbook_path: str,
    extravars: dict[str, Any],
    quiet: bool = True,
    tags: str | None = None,
) -> ansible_runner.Runner:
    """
    Run an Ansible playbook with the given extra variables.

    - `playbook_path`: Path to the playbook file relative to `PLAYBOOKS_ROOT`
    - `extravars`: Dictionary of variables to pass to the playbook
    - `quiet`: If True, suppress stdout/stderr
    - `tags`: Optional comma-separated tags to run
    """

    all_vars = get_env_vars()
    all_vars.update(extravars)

    # Build cmdline
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
    admin_password: str,
    db_password: str,
    force: bool = False,
) -> ansible_runner.Runner:
    """
    Provision a new tenant using Ansible.

    Args:
        tenant_tag: Unique identifier for the tenant
        service_type: Type of site (flarum, mediawiki, wordpress)
        admin_email: Administrator email address
        admin_password: Administrator password
        db_password: Database password for the tenant
        force: If True, overwrite existing tenant

    Returns:
        ansible_runner.Runner object with results
    """
    extravars = {
        "tenant_tag": tenant_tag,
        "service_type": service_type,
        "tenant_admin_email": admin_email,
        "tenant_admin_password": admin_password,
        "tenant_db_password": db_password,
        "force": force,
    }

    return run_playbook("provision/main.yml", extravars)


async def remove_tenant(
    tenant_tag: str,
    service_type: str,
    skip_backup: bool = False,
) -> ansible_runner.Runner:
    """
    Remove a tenant using Ansible.

    Args:
        tenant_tag: Unique identifier for the tenant
        service_type: Type of site (flarum, mediawiki, wordpress)
        skip_backup: If True, skip backup before removal (GDPR full deletion)

    Returns:
        ansible_runner.Runner object with results
    """
    extravars = {
        "tenant_tag": tenant_tag,
        "service_type": service_type,
        "skip_backup": skip_backup,
    }

    return run_playbook("removal/main.yml", extravars)


async def backup_tenant(
    tenant_tag: str,
    service_type: str,
) -> ansible_runner.Runner:
    """
    Backup a tenant using Ansible.

    Args:
        tenant_tag: Unique identifier for the tenant
        service_type: Type of site (flarum, mediawiki, wordpress)

    Returns:
        ansible_runner.Runner object with results
    """
    extravars = {
        "tenant_tag": tenant_tag,
        "service_type": service_type,
        "skip_backup": False,
    }

    return run_playbook("removal/main.yml", extravars, tags="backup")


class AnsibleError(Exception):
    """Raised when an Ansible playbook fails."""
