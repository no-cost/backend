import typing as t

import bcrypt
import fastapi as fa
from fastapi import BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Site
from database.session import get_session
from settings import VARS
from site_manager import provision_site
from site_manager.custom_domains import write_nginx_map

V1_SIGNUP = fa.APIRouter(prefix="/signup", tags=["signup"])


class SignupRequest(BaseModel):
    tag: str
    email: EmailStr
    password: str
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

    hashed_password = bcrypt.hashpw(
        request.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    site = Site(
        tag=request.tag,
        admin_email=request.email,
        admin_password=hashed_password,
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

    background_tasks.add_task(provision_site, site)
    background_tasks.add_task(write_nginx_map, db)

    return SignupResponse(
        message="Your site is now being installed. You will receive an email when it is ready to use.",
        site_tag=site.tag,
        hostname=site.hostname,
    )
