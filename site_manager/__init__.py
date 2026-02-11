from database.models import Site
from settings import VARS
from site_manager.runner import (
    backup_tenant,
    provision_tenant,
    remove_tenant,
)
from utils import run_cmd


def provision_site(
    site: Site,
    reset_token: str,
    force: bool = False,
) -> None:
    provision_tenant(
        tenant_tag=site.tag,
        service_type=site.site_type,
        hostname=site.hostname,
        admin_email=site.admin_email,
        reset_token=reset_token,
        force=force,
    )


async def upgrade_site(
    site: Site,
) -> None:
    tenant_root = VARS["paths"]["tenants"]["root"] / site.tag
    tenant_pub_dir = tenant_root / "public"
    tenant_user = f"tenant_{site.tag}"

    match site.site_type:
        case "flarum":
            await run_cmd(
                "php flarum migrate",
                user=tenant_user,
                cwd=tenant_root / "app",  # flarum root is in /app/
            )
            await run_cmd(
                "php flarum cache:clear",
                user=tenant_user,
                cwd=tenant_root / "app",
            )
        case "mediawiki":
            await run_cmd(
                "php maintenance/run.php update --quick",
                user=tenant_user,
                cwd=tenant_pub_dir,
            )
        case "wordpress":
            await run_cmd("wp cache flush", user=tenant_user, cwd=tenant_pub_dir)
            await run_cmd("wp core update-db", user=tenant_user, cwd=tenant_pub_dir)


def remove_site(
    site: Site,
    skip_backup: bool = False,
) -> None:
    remove_tenant(
        tenant_tag=site.tag,
        service_type=site.site_type,
        skip_backup=skip_backup,
    )


def backup_site(
    site: Site,
    service_type: str,
) -> None:
    # TODO: do this from Python side, no need for Ansible?
    backup_tenant(
        tenant_tag=site.tag,
        service_type=service_type,
    )
