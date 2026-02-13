import typing as t

import fastapi as fa
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.service_settings.mediawiki import MEDIAWIKI
from database.models import Site
from database.session import get_session
from settings import VARS
from site_manager import upgrade_site
from site_manager.custom_domains import (
    CNAMENotFoundError,
    DomainAlreadyLinkedError,
    link_custom_domain,
    rewrite_urls,
    unlink_custom_domain,
    write_nginx_maps,
)
from utils.auth import get_current_site

V1_SETTINGS = fa.APIRouter(prefix="/settings", tags=["settings"])
V1_SETTINGS.include_router(MEDIAWIKI)


@V1_SETTINGS.get("/allowed-domains")
async def get_allowed_domains(
    _site: t.Annotated[Site, fa.Depends(get_current_site)],
) -> list[str]:
    return VARS["allowed_domains"]


class LinkDomainBody(BaseModel):
    domain: str


@V1_SETTINGS.post("/link-domain")
async def link_domain(
    body: LinkDomainBody,
    site: t.Annotated[Site, fa.Depends(get_current_site)],
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
) -> dict:
    """Link a custom domain to the authenticated user's site."""

    if not site.has_donor_perks():
        raise fa.HTTPException(
            status_code=403, detail="Custom domains are available to donors only"
        )

    try:
        await link_custom_domain(db, site, body.domain)
    except DomainAlreadyLinkedError as e:
        raise fa.HTTPException(status_code=409, detail=str(e))
    except CNAMENotFoundError as e:
        raise fa.HTTPException(status_code=422, detail=str(e))

    return {"message": f"Domain '{body.domain}' has been linked to your site."}


class UnlinkDomainBody(BaseModel):
    parent_domain: str


@V1_SETTINGS.delete("/link-domain")
async def unlink_domain(
    body: UnlinkDomainBody,
    site: t.Annotated[Site, fa.Depends(get_current_site)],
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
) -> dict:
    """Unlink a custom domain from the authenticated user's site, restoring a chosen default hostname."""

    if body.parent_domain not in VARS["allowed_domains"]:
        raise fa.HTTPException(
            status_code=422,
            detail=f"Invalid parent domain. Choose one of: {', '.join(VARS['allowed_domains'])}",
        )

    canonical = f"{site.tag}.{body.parent_domain}"
    if site.hostname == canonical:
        raise fa.HTTPException(
            status_code=409, detail="No custom domain is linked to this site"
        )

    await unlink_custom_domain(db, site, canonical)
    return {
        "message": f"Custom domain has been unlinked. Your site is now at '{canonical}'."
    }


class ChangeParentDomainBody(BaseModel):
    parent_domain: str


@V1_SETTINGS.patch("/parent-domain")
async def change_parent_domain(
    body: ChangeParentDomainBody,
    site: t.Annotated[Site, fa.Depends(get_current_site)],
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
) -> dict:
    """Switch the site to a different parent domain."""

    if body.parent_domain not in VARS["allowed_domains"]:
        raise fa.HTTPException(
            status_code=422,
            detail=f"Invalid parent domain. Choose one of: {', '.join(VARS['allowed_domains'])}",
        )

    new_hostname = f"{site.tag}.{body.parent_domain}"
    if site.hostname == new_hostname:
        raise fa.HTTPException(
            status_code=409, detail="Site is already on this parent domain"
        )

    # only allow switching between internal domains, not from a custom domain
    if site.get_parent_domain() not in VARS["allowed_domains"]:
        raise fa.HTTPException(
            status_code=409,
            detail="Unlink your custom domain first before changing the parent domain",
        )

    old_hostname = site.hostname
    site.hostname = new_hostname
    await db.commit()
    await write_nginx_maps(db)
    await rewrite_urls(site, old_hostname)

    return {"message": f"Parent domain changed. Your site is now at '{new_hostname}'."}


@V1_SETTINGS.post("/fixup")
async def fixup(
    site: t.Annotated[Site, fa.Depends(get_current_site)],
) -> dict:
    """Run migrations and cache clears for the authenticated user's site."""

    await upgrade_site(site)
    return {"message": f"Fixup completed for site '{site.tag}'."}
