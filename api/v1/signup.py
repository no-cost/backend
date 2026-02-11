import asyncio
import typing as t
from datetime import datetime

import bcrypt
import fastapi as fa
from fastapi import BackgroundTasks
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.auth import create_reset_token
from database.models import Site
from database.session import async_session_factory, get_session
from settings import VARS
from site_manager import provision_site
from site_manager.custom_domains import write_nginx_maps
from utils import random_string, validate_tag, verify_turnstile

V1_SIGNUP = fa.APIRouter(prefix="/signup", tags=["signup"])


class SignupRequest(BaseModel):
    tag: str
    email: EmailStr
    site_type: str
    parent_domain: str
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
):
    """
    Create and install a new site.

    The site installation happens in the background after the response is sent.
    """

    await verify_turnstile(request.turnstile_token)

    if request.site_type not in VARS["available_site_types"]:
        raise fa.HTTPException(
            status_code=400,
            detail="Invalid site type.",
        )

    if request.parent_domain not in VARS["allowed_domains"]:
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
        hostname=f"{request.tag}.{request.parent_domain}",
    )

    try:
        db.add(site)
        await db.commit()
    except IntegrityError as e:
        raise fa.HTTPException(
            status_code=400, detail="A site with this tag already exists"
        ) from e

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

        await asyncio.to_thread(provision_site, site, reset_token)

        site.installed_at = datetime.now()
        await db.commit()

        await write_nginx_maps(db)
