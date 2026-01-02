"""
Sites API routes for managing tenant sites.
"""

import typing as t
from datetime import datetime

import fastapi as fa
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Site
from database.session import get_session
from site_manager import AnsibleError, install_site, remove_site

V1_SITES = fa.APIRouter(prefix="/sites", tags=["sites"])


class SiteResponse(BaseModel):
    """Response model for a site."""

    id: str
    site_type: str
    hostname: str | None
    admin_email: str
    installed_at: datetime | None
    created_at: datetime


class RemoveSiteRequest(BaseModel):
    """Request model for removing a site."""

    skip_backup: bool = False


@V1_SITES.get("/", response_model=list[SiteResponse])
async def list_sites(
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
) -> list[Site]:
    """
    List all sites.
    """
    result = await db.execute(
        select(Site).where(Site.removed_at.is_(None)).order_by(Site.created_at.desc())
    )
    return list(result.scalars().all())


@V1_SITES.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: str,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
) -> Site:
    """
    Get a site by ID.
    """
    site = await db.get(Site, site_id)
    if site is None or site.removed_at is not None:
        raise fa.HTTPException(status_code=404, detail="Site not found")
    return site


@V1_SITES.post("/{site_id}/install")
async def install_site_endpoint(
    site_id: str,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
) -> dict:
    """
    Install a site that was created but not yet installed.
    """
    site = await db.get(Site, site_id)
    if site is None or site.removed_at is not None:
        raise fa.HTTPException(status_code=404, detail="Site not found")

    if site.installed_at is not None:
        raise fa.HTTPException(status_code=400, detail="Site already installed")

    try:
        await install_site(site)
    except AnsibleError as e:
        raise fa.HTTPException(
            status_code=500, detail=f"Failed to install site: {e}"
        ) from e

    return {"message": "Site installed successfully"}


@V1_SITES.delete("/{site_id}")
async def delete_site(
    site_id: str,
    request: RemoveSiteRequest,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
) -> dict:
    """
    Remove a site.

    By default, creates a backup before removal. Set skip_backup=true for
    GDPR-compliant full deletion with no backup.
    """

    site = await db.get(Site, site_id)
    if site is None or site.removed_at is not None:
        raise fa.HTTPException(status_code=404, detail="Site not found")

    try:
        await remove_site(
            tenant_tag=site.tag,
            service_type=site.site_type,
            skip_backup=request.skip_backup,
        )
    except AnsibleError as e:
        raise fa.HTTPException(
            status_code=500, detail=f"Failed to remove site: {e}"
        ) from e

    # Mark as removed in database
    site.removed_at = datetime.now()
    site.removal_reason = "GDPR deletion" if request.skip_backup else "User requested"
    await db.commit()

    return {"message": "Site removed successfully"}
