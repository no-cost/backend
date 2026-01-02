"""
Site manager module for tenant lifecycle management.

This module provides high-level functions to create, remove, and backup
tenant sites using Ansible playbooks via ansible-runner.
"""

import secrets
from contextlib import asynccontextmanager
from datetime import datetime

from database import models
from database.session import get_session
from site_manager.ansible_runner import (
    AnsibleError,
    backup_tenant,
    provision_tenant,
    remove_tenant,
)

__all__ = [
    "create_site",
    "remove_site",
    "backup_site",
    "install_site",
    "AnsibleError",
]


async def create_site(
    tenant_tag: str,
    service_type: str,
    admin_email: str,
    admin_password: str,
    db_password: str | None = None,
    force: bool = False,
) -> None:
    """
    Create a new tenant site.

    This is the main entry point for creating sites from CLI or API.
    It provisions the site using Ansible and does NOT create a database record.

    Args:
        tenant_tag: Unique identifier for the tenant (4 chars)
        service_type: Type of site (flarum, mediawiki, wordpress)
        admin_email: Administrator email address
        admin_password: Administrator password
        db_password: Database password (generated if not provided)
        force: If True, overwrite existing tenant
    """
    # Generate DB password if not provided
    if db_password is None:
        db_password = secrets.token_urlsafe(32)

    # Run the Ansible playbook
    await provision_tenant(
        tenant_tag=tenant_tag,
        service_type=service_type,
        admin_email=admin_email,
        admin_password=admin_password,
        db_password=db_password,
        force=force,
    )


async def install_site(site: models.Site) -> None:
    """
    Install a site from a Site model instance.

    This is used by the API when a site is created via the web interface.
    It provisions the site and updates the database record.

    Args:
        site: Site model instance with tenant details
    """
    # Generate a secure DB password
    db_password = secrets.token_urlsafe(32)

    # Run the Ansible playbook
    await provision_tenant(
        tenant_tag=site.tag,
        service_type=site.site_type,
        admin_email=site.admin_email,
        admin_password=site.admin_password,
        db_password=db_password,
    )

    # Update the site record
    async with asynccontextmanager(get_session)() as session:
        site.installed_at = datetime.now()
        session.add(site)
        await session.commit()


async def remove_site(
    tenant_tag: str,
    service_type: str,
    skip_backup: bool = False,
) -> None:
    """
    Remove a tenant site.

    This is the main entry point for removing sites from CLI or API.

    Args:
        tenant_tag: Unique identifier for the tenant
        service_type: Type of site (flarum, mediawiki, wordpress)
        skip_backup: If True, skip backup before removal (GDPR full deletion)
    """
    await remove_tenant(
        tenant_tag=tenant_tag,
        service_type=service_type,
        skip_backup=skip_backup,
    )


async def backup_site(
    tenant_tag: str,
    service_type: str,
) -> None:
    """
    Backup a tenant site.

    Creates a backup of the site files and database in /backup/attic/.

    Args:
        tenant_tag: Unique identifier for the tenant
        service_type: Type of site (flarum, mediawiki, wordpress)
    """
    await backup_tenant(
        tenant_tag=tenant_tag,
        service_type=service_type,
    )
