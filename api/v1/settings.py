import asyncio
import shutil
import tempfile
import typing as t
from datetime import datetime
from pathlib import Path

import fastapi as fa
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from database.models import Site
from database.session import get_session
from site_manager import backup_site, remove_site
from utils import get_client_ip, get_current_site

V1_SETTINGS = fa.APIRouter(prefix="/settings", tags=["settings"])

# sensitive files to strip from data exports, per service type
EXPORT_EXCLUDES: dict[str, list[str]] = {
    "flarum": ["/etc", "/etc/config.json", "/logs", "/logs/**"],
    "mediawiki": ["/etc", "/etc/config.json", "/logs", "/logs/**"],
    "wordpress": ["/etc", "/etc/config.json", "/logs", "/logs/**"],
}


class SiteResponse(BaseModel):
    tag: str
    site_type: str
    hostname: str | None
    admin_email: str
    installed_at: datetime | None
    created_at: datetime


@V1_SETTINGS.delete("/")
async def delete_site(
    site: t.Annotated[Site, fa.Depends(get_current_site)],
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
    background_tasks: fa.BackgroundTasks,
    client_ip: t.Annotated[str | None, fa.Depends(get_client_ip)],
) -> dict:
    """Remove the authenticated user's site. Does not create a backup."""

    site.removed_at = datetime.now()
    site.removed_ip = client_ip
    site.removal_reason = "Requested by you through settings"

    background_tasks.add_task(
        remove_site, site, skip_backup=True, reason=site.removal_reason
    )
    await db.commit()

    return {
        "message": "Your site is being removed. You will receive an email when the process is complete. If you haven't received anything, please contact us."
    }


@V1_SETTINGS.get("/export")
async def export_data(
    site: t.Annotated[Site, fa.Depends(get_current_site)],
) -> FileResponse:
    """Export the authenticated user's site data as a downloadable archive."""

    excludes = EXPORT_EXCLUDES.get(site.site_type, [])

    tmp_dir = tempfile.mkdtemp(prefix="nocost_export_")
    backup_dir = str(Path(tmp_dir) / site.tag)
    archive_path = f"{backup_dir}.tar.gz"

    try:
        await asyncio.to_thread(
            backup_site,
            site,
            additional_excludes=excludes,
            backup_dir=backup_dir,
            include_readme=True,
        )
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise fa.HTTPException(status_code=500, detail="Export failed")

    return FileResponse(
        path=archive_path,
        media_type="application/gzip",
        filename=f"{site.tag}-export.tar.gz",
        background=BackgroundTask(shutil.rmtree, tmp_dir, ignore_errors=True),
    )
