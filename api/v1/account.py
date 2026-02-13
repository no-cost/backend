import asyncio
import shutil
import tempfile
import typing as t
from datetime import datetime
from pathlib import Path

import bcrypt
import fastapi as fa
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from database.models import Site
from database.session import get_session
from settings import VARS
from site_manager import backup_site, remove_site
from utils.auth import (
    create_access_token,
    create_reset_token,
    decode_reset_token,
    get_current_site,
    password_fingerprint,
    verify_password,
)
from utils.ip import get_client_ip
from utils.mail import send_mail
from utils.turnstile import verify_turnstile

V1_ACCOUNT = fa.APIRouter(prefix="/account", tags=["account"])

EXPORT_EXCLUDES: dict[str, list[str]] = {
    "flarum": ["/etc", "/etc/config.json", "/logs", "/logs/**"],
    "mediawiki": ["/etc", "/etc/config.json", "/logs", "/logs/**"],
    "wordpress": ["/etc", "/etc/config.json", "/logs", "/logs/**"],
}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@V1_ACCOUNT.post("/login", response_model=TokenResponse)
async def login(
    form: t.Annotated[OAuth2PasswordRequestForm, fa.Depends()],
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
    client_ip: t.Annotated[str | None, fa.Depends(get_client_ip)],
):
    site = await Site.get_by_tag_or_hostname(db, form.username)

    if site is None or not verify_password(form.password, site.admin_password):
        raise fa.HTTPException(status_code=401, detail="Invalid credentials")

    site.last_login_at = datetime.now()
    site.last_login_ip = client_ip
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(site.tag), token_type="bearer"
    )


class AccountResponse(BaseModel):
    tag: str
    admin_email: EmailStr
    site_type: str
    hostname: str
    donated_amount: float | None
    installed_at: datetime | None
    created_at: datetime


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


class ResetPasswordRequestBody(BaseModel):
    site: str
    turnstile_token: str


@V1_ACCOUNT.post("/reset-password/request")
async def request_password_reset(
    body: ResetPasswordRequestBody,
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
):
    await verify_turnstile(body.turnstile_token)

    site = await Site.get_by_tag_or_hostname(db, body.site)
    if site is None:
        return {
            "message": "If a site with this identifier exists, a password reset link has been sent to the site's admin email."
        }

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

    return {
        "message": "If a site with this identifier exists, a password reset link has been sent to the site's admin email."
    }


class ResetPasswordBody(BaseModel):
    token: str
    password: str


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

    if pfp != password_fingerprint(site.admin_password):
        raise fa.HTTPException(
            status_code=400, detail="Reset link is invalid or has already been used"
        )

    site.admin_password = bcrypt.hashpw(
        body.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    await db.commit()

    return {"message": "Password has been set successfully."}


@V1_ACCOUNT.get("/export")
async def export_data(
    site: t.Annotated[Site, fa.Depends(get_current_site)],
) -> FileResponse:
    """Export the authenticated user's site data as a downloadable archive."""

    excludes = EXPORT_EXCLUDES.get(site.site_type, [])

    tmp_dir = tempfile.mkdtemp(prefix="nocost_export_")
    backup_dir = str(Path(tmp_dir) / site.tag)
    archive_path = f"{backup_dir}.tar.gz"

    try:
        await asyncio.to_thread(
            backup_site,
            site,
            additional_excludes=excludes,
            backup_dir=backup_dir,
            include_readme=True,
        )
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise fa.HTTPException(status_code=500, detail="Export failed")

    return FileResponse(
        path=archive_path,
        media_type="application/gzip",
        filename=f"{site.tag}-export.tar.gz",
        background=BackgroundTask(shutil.rmtree, tmp_dir, ignore_errors=True),
    )


@V1_ACCOUNT.delete("/")
async def delete_site(
    site: t.Annotated[Site, fa.Depends(get_current_site)],
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
    background_tasks: fa.BackgroundTasks,
    client_ip: t.Annotated[str | None, fa.Depends(get_client_ip)],
) -> dict:
    """Remove the authenticated user's site. Does not create a backup."""

    site.removed_at = datetime.now()
    site.removed_ip = client_ip
    site.removal_reason = "Requested by you through settings"

    background_tasks.add_task(
        remove_site, site, skip_backup=True, reason=site.removal_reason
    )
    await db.commit()

    return {
        "message": "Your site is being removed. You will receive an email when the process is complete. If you haven't received anything, please contact us."
    }
