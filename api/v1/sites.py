import typing as t
from datetime import datetime

import fastapi as fa
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Site
from database.session import get_session
from site_manager import remove_site

V1_SITES = fa.APIRouter(prefix="/sites", tags=["sites"])


class SiteResponse(BaseModel):
    tag: str
    site_type: str
    hostname: str | None
    admin_email: str
    installed_at: datetime | None
    created_at: datetime


# TODO: remove in prod:
@V1_SITES.get("/", response_model=list[SiteResponse])
async def list_sites(
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
) -> list[Site]:
    """
    List all installed sites.
    """

    result = await db.execute(
        select(Site).where(Site.removed_at.is_(None)).order_by(Site.created_at.desc())
    )
    return list[Site](result.scalars().all())


# TODO: remove in prod:
@V1_SITES.get("/{site_tag}", response_model=SiteResponse)
async def get_site(
    site_tag: str,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
) -> Site:
    """
    Get a site by tag.
    """

    site = await db.get(Site, site_tag)
    if site is None or site.removed_at is not None:
        raise fa.HTTPException(status_code=404, detail="Site not found")
    return site


# TODO: ensure auth!!!!!
@V1_SITES.delete("/{site_tag}")
async def delete_site(
    site_tag: str,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
    background_tasks: fa.BackgroundTasks,
) -> dict:
    """
    Remove a site. Does not create a backup.
    """

    site = await db.get(Site, site_tag)
    if site is None or site.removed_at is not None:
        raise fa.HTTPException(status_code=404, detail="Site not found")

    background_tasks.add_task(remove_site, site, skip_backup=True)

    site.removed_at = datetime.now()
    site.removal_reason = "User requested"
    await db.commit()

    return {"message": "Site removed successfully"}
