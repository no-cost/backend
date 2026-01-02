import typing as t

import bcrypt
import fastapi as fa
from fastapi import BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Site
from database.session import get_session
from settings import Settings
from site_manager import install_site

V1_SIGNUP = fa.APIRouter(prefix="/signup", tags=["signup"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    site_type: str
    parent_domain: str


class SignupResponse(BaseModel):
    message: str
    site_id: str
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
    # Validate site type
    if request.site_type not in Settings.AVAILABLE_SITE_TYPES:
        raise fa.HTTPException(
            status_code=400,
            detail=f"Invalid site type. Available: {Settings.AVAILABLE_SITE_TYPES}",
        )

    # Validate parent domain
    if request.parent_domain not in Settings.ALLOWED_DOMAINS:
        raise fa.HTTPException(
            status_code=400,
            detail=f"Invalid parent domain. Available: {Settings.ALLOWED_DOMAINS}",
        )

    # Hash the password
    hashed_password = bcrypt.hashpw(
        request.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    # Create the site record (ID is auto-generated)
    site = Site(
        admin_email=request.email,
        admin_password=hashed_password,
        site_type=request.site_type,
        hostname=None,  # Will be set after installation
        chroot_dir="",  # Will be set after installation
    )

    db.add(site)
    await db.commit()
    await db.refresh(site)

    # Set hostname based on generated ID
    site.hostname = f"{site.tag}.{request.parent_domain}"
    site.chroot_dir = f"/srv/host/{site.tag}"
    await db.commit()

    # Install site in background
    background_tasks.add_task(install_site, site)

    return SignupResponse(
        message="Site created. Installation in progress.",
        site_tag=site.tag,
        hostname=site.hostname,
    )
