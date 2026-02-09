import typing as t
import secrets

import bcrypt
import fastapi as fa
from fastapi import BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.auth import create_reset_token
from database.models import Site
from database.session import get_session
from settings import VARS
from site_manager import provision_site
from site_manager.custom_domains import write_nginx_map

V1_SIGNUP = fa.APIRouter(prefix="/signup", tags=["signup"])


class SignupRequest(BaseModel):
    tag: str
    email: EmailStr
    site_type: str
    parent_domain: str


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
        secrets.token_bytes(32), bcrypt.gensalt()
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

    reset_token = create_reset_token(site.tag)
    background_tasks.add_task(provision_site, site, reset_token)
    background_tasks.add_task(write_nginx_map, db)

    return SignupResponse(
        message="Your site is being installed. Check your email to set your password.",
        site_tag=site.tag,
        hostname=site.hostname,
    )
