import typing as t
from datetime import datetime

import fastapi as fa
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.auth import get_current_site
from database.models import Site
from database.session import get_session
from site_manager import remove_site
from utils import get_client_ip

V1_SETTINGS = fa.APIRouter(prefix="/settings", tags=["settings"])


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
    """
    Remove the authenticated user's site. Does not create a backup.
    """

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
