import typing as t
from datetime import datetime

import fastapi as fa
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.auth import create_access_token, get_current_site, verify_password
from database.models import Site
from database.session import get_session

V1_ACCOUNT = fa.APIRouter(prefix="/account", tags=["account"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str


class AccountResponse(BaseModel):
    tag: str
    admin_email: str
    site_type: str
    hostname: str
    donated_amount: float | None
    installed_at: datetime | None
    created_at: datetime


@V1_ACCOUNT.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
):
    result = await db.execute(
        select(Site).where(Site.tag == request.username, Site.removed_at.is_(None))
    )
    site = result.scalar_one_or_none()

    if site is None or not verify_password(request.password, site.admin_password):
        raise fa.HTTPException(status_code=401, detail="Invalid credentials")

    site.last_login_at = datetime.now()
    await db.commit()

    return LoginResponse(token=create_access_token(site.tag))


@V1_ACCOUNT.get("/", response_model=AccountResponse)
async def account(
    site: t.Annotated[Site, fa.Depends(get_current_site)],
):
    return AccountResponse(
        tag=site.tag,
        admin_email=site.admin_email,
        site_type=site.site_type,
        hostname=site.hostname,
        donated_amount=site.donated_amount,
        installed_at=site.installed_at,
        created_at=site.created_at,
    )
