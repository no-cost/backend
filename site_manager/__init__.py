from database.models import Site
from site_manager.runner import (
    backup_tenant,
    provision_tenant,
    remove_tenant,
)


async def provision_site(
    site: Site,
    force: bool = False,
) -> None:
    """
    Provisions/creates/installs a new tenant site and updates the site in the database.
    """

    await provision_tenant(
        tenant_tag=site.tag,
        service_type=site.site_type,
        hostname=site.hostname,
        admin_email=site.admin_email,
        force=force,
    )


async def remove_site(
    site: Site,
    reason: str | None = None,
    skip_backup: bool = False,
) -> None:
    """
    Removes a tenant site and updates the site in the database.
    """

    remove_tenant(
        tenant_tag=site.tag,
        service_type=site.site_type,
        skip_backup=skip_backup,
    )


async def backup_site(
    site: Site,
    service_type: str,
) -> None:
    """
    Backup a tenant site. Should be run periodically by a cron job.
    """

    # TODO: do this from Python side, no need for Ansible?
    await backup_tenant(
        tenant_tag=site.tag,
        service_type=service_type,
    )
