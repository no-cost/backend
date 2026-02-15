import tempfile
from pathlib import Path

from database.models import Site
from settings import VARS
from site_manager.runner import (
    backup_tenant,
    provision_tenant,
    remove_tenant,
    restore_tenant,
    sync_tenant_files,
)
from utils.cmd import run_cmd, run_cmd_as_tenant


def provision_site(
    site: Site,
    reset_token: str,
    force: bool = False,
    send_email: bool = True,
):
    return provision_tenant(
        tenant_tag=site.tag,
        service_type=site.site_type,
        hostname=site.hostname,
        admin_email=site.admin_email,
        reset_token=reset_token,
        force=force,
        send_email=send_email,
    )


async def upgrade_site(
    site: Site,
    sync_files: bool = False,
) -> None:
    tenant_root = Path(VARS["paths"]["tenants"]["root"]) / site.tag
    tenant_pub_dir = tenant_root / "public"
    tenant_user = f"tenant_{site.tag}"

    if sync_files:
        sync_tenant_files(tenant_tag=site.tag, service_type=site.site_type)

    match site.site_type:
        case "flarum":
            app_dir = tenant_root / "app"
            await run_cmd_as_tenant(tenant_user, "php flarum migrate", cwd=app_dir)
            await run_cmd_as_tenant(tenant_user, "php flarum cache:clear", cwd=app_dir)
        case "mediawiki":
            await run_cmd_as_tenant(
                tenant_user,
                "php maintenance/run.php update --quick",
                cwd=tenant_pub_dir,
            )
        case "wordpress":
            await run_cmd_as_tenant(tenant_user, "wp cache flush", cwd=tenant_pub_dir)
            await run_cmd_as_tenant(
                tenant_user, "wp core update-db", cwd=tenant_pub_dir
            )


def remove_site(
    site: Site,
    skip_backup: bool = False,
    send_email: bool = True,
    reason: str | None = None,
):
    return remove_tenant(
        tenant_tag=site.tag,
        service_type=site.site_type,
        skip_backup=skip_backup,
        send_email=send_email,
        admin_email=site.admin_email,
        hostname=site.hostname,
        reason=reason,
    )


def backup_site(
    site: Site,
    periodic: bool = False,
    delete_older_than_days: int = 7,
    additional_excludes: list[str] = [],
    backup_dir: str | None = None,
    include_readme: bool = False,
):
    return backup_tenant(
        tenant_tag=site.tag,
        service_type=site.site_type,
        periodic=periodic,
        delete_older_than_days=delete_older_than_days,
        additional_excludes=additional_excludes,
        backup_dir=backup_dir,
        include_readme=include_readme,
    )


def restore_site(
    site: Site,
    backup_mode: str = "attic",
    backup_date: str | None = None,
):
    return restore_tenant(
        tenant_tag=site.tag,
        service_type=site.site_type,
        backup_mode=backup_mode,
        backup_date=backup_date,
    )


async def write_tenant_file(site: Site, dest_rel: str, content: bytes) -> None:
    tenant_root = Path(VARS["paths"]["tenants"]["root"]) / site.tag
    dest = tenant_root / dest_rel
    tenant_user = f"tenant_{site.tag}"

    # api server runs as different user than the tenant,
    # so we need to upload as temp and then ensure correct ownership
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        await run_cmd_as_tenant(tenant_user, f"mkdir -p {dest.parent}")
        await run_cmd(f"sudo mv {tmp_path} {dest}")
        await run_cmd(f"sudo chmod 644 {dest}")
        await run_cmd(f"sudo chown {tenant_user}:{tenant_user} {dest}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
