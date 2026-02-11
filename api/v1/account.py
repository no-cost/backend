import typing as t
from datetime import datetime

import bcrypt
import fastapi as fa
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.auth import (
    _password_fingerprint,
    create_access_token,
    create_reset_token,
    decode_reset_token,
    get_current_site,
    verify_password,
)
from database.models import Site
from database.session import get_session
from settings import VARS
from utils import get_client_ip, send_mail, verify_turnstile

V1_ACCOUNT = fa.APIRouter(prefix="/account", tags=["account"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str


class AccountResponse(BaseModel):
    tag: str
    admin_email: EmailStr
    site_type: str
    hostname: str
    donated_amount: float | None
    installed_at: datetime | None
    created_at: datetime


class ResetPasswordRequestBody(BaseModel):
    site: str
    turnstile_token: str


class ResetPasswordBody(BaseModel):
    token: str
    password: str


@V1_ACCOUNT.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
    client_ip: t.Annotated[str | None, fa.Depends(get_client_ip)],
):
    site = await Site.get_by_tag_or_hostname(db, request.username)

    if site is None or not verify_password(request.password, site.admin_password):
        raise fa.HTTPException(status_code=401, detail="Invalid credentials")

    site.last_login_at = datetime.now()
    site.last_login_ip = client_ip
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


@V1_ACCOUNT.post("/reset-password/request")
async def request_password_reset(
    body: ResetPasswordRequestBody,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
):
    await verify_turnstile(body.turnstile_token)

    site = await Site.get_by_tag_or_hostname(db, body.site)
    if site is None:
        raise fa.HTTPException(
            status_code=404, detail="No site found with this tag or hostname."
        )

    token = create_reset_token(site.tag, site.admin_password)
    link = f"https://{VARS['main_domain']}/reset-password?token={token}"

    send_mail(
        to=site.admin_email,
        subject="Password reset — no-cost.site",
        body=(
            f"A password reset was requested for your site '{site.tag}'.\n\n"
            f"To set a new password, visit the following link:\n{link}\n\n"
            "If you did not request this, you can safely ignore this e-mail."
        ),
    )

    return {"message": "A password reset link has been sent to the site's admin email."}


@V1_ACCOUNT.post("/reset-password")
async def reset_password(
    body: ResetPasswordBody,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
):
    """Set a new password using a valid reset token."""

    tag, pfp = decode_reset_token(body.token)
    site = await Site.get_by_tag_or_hostname(db, tag)
    if site is None:
        raise fa.HTTPException(status_code=404, detail="Site not found")

    if pfp != _password_fingerprint(site.admin_password):
        raise fa.HTTPException(
            status_code=400, detail="Reset link is invalid or has already been used"
        )

    site.admin_password = bcrypt.hashpw(
        body.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    await db.commit()

    return {"message": "Password has been set successfully."}
