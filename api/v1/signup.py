import asyncio
import typing as t
from datetime import datetime

import bcrypt
import fastapi as fa
from fastapi import BackgroundTasks
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Site
from database.session import async_session_factory, get_session
from settings import VARS
from site_manager import provision_site
from site_manager.custom_domains import write_nginx_maps
from utils import is_tag_blacklisted, random_string, validate_tag
from utils.auth import create_reset_token
from utils.ip import get_client_ip
from utils.turnstile import verify_turnstile

V1_SIGNUP = fa.APIRouter(prefix="/signup", tags=["signup"])


@V1_SIGNUP.get("/allowed-domains")
async def get_allowed_domains() -> list[str]:
    return VARS["allowed_domains"]


class SignupRequest(BaseModel):
    tag: str
    email: EmailStr
    site_type: str
    parent_domain: str | None = None
    turnstile_token: str

    @field_validator("tag")
    @classmethod
    def tag_must_be_alphanumeric(cls, v: str) -> str:
        return validate_tag(v)


class SignupResponse(BaseModel):
    message: str
    site_tag: str
    hostname: str


@V1_SIGNUP.post("/", response_model=SignupResponse)
async def signup(
    request: SignupRequest,
    background_tasks: BackgroundTasks,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
    client_ip: t.Annotated[str | None, fa.Depends(get_client_ip)],
    x_test_token: t.Annotated[str | None, fa.Header()] = None,
):
    """Create and install a new site. The site installation happens in the background after the response is sent."""

    if not x_test_token == VARS["integration_test_token"]:
        await verify_turnstile(request.turnstile_token)
        if is_tag_blacklisted(request.tag):
            raise fa.HTTPException(status_code=400, detail="This tag is not allowed.")

    if request.site_type not in VARS["available_site_types"]:
        raise fa.HTTPException(
            status_code=400,
            detail="Invalid site type.",
        )

    parent_domain = request.parent_domain or VARS["main_domain"]
    if parent_domain not in VARS["allowed_domains"]:
        raise fa.HTTPException(
            status_code=400,
            detail="Invalid parent domain.",
        )

    # temporary random password (user is expected to set one via email link)
    throwaway_password = bcrypt.hashpw(
        random_string(32).encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    site = Site(
        tag=request.tag,
        admin_email=request.email,
        admin_password=throwaway_password,
        site_type=request.site_type,
        created_ip=client_ip,
        hostname=f"{request.tag}.{parent_domain}",
    )

    # if a deleted site with this tag exists, purge it to free the tag
    existing = await db.get(Site, request.tag)
    if existing:
        if existing.removed_at is None:
            raise fa.HTTPException(
                status_code=400, detail="A site with this tag already exists"
            )
        await db.delete(existing)
        await db.flush()

    db.add(site)
    await db.commit()

    reset_token = create_reset_token(site.tag, site.admin_password)
    background_tasks.add_task(_provision_and_finalize, site.tag, reset_token)

    return SignupResponse(
        message="Your site is being installed. Check your email to set your password.",
        site_tag=site.tag,
        hostname=site.hostname,
    )


async def _provision_and_finalize(site_tag: str, reset_token: str):
    async with async_session_factory() as db:
        site = await db.get(Site, site_tag)

        # so it doesn't block the event loop, so it can serve other reqs
        # it still waits here before setting installed_at
        await asyncio.to_thread(provision_site, site, reset_token)

        site.installed_at = datetime.now()
        await db.commit()

        await write_nginx_maps(db)
