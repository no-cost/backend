import hashlib
import typing as t
from datetime import datetime, timedelta, timezone

import bcrypt
import fastapi as fa
import jwt
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Site
from database.session import get_session
from settings import VARS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/account/login")


async def get_current_site(
    token: t.Annotated[str, fa.Depends(oauth2_scheme)],
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
) -> Site:
    """Dependency that extracts the JWT, validates it, and returns the Site associated with the token."""

    tag = decode_access_token(token)

    site = await db.execute(
        select(Site).where(Site.tag == tag, Site.removed_at.is_(None))
    )
    site = site.scalar_one_or_none()

    if site is None:
        raise fa.HTTPException(status_code=404, detail="Site not found")

    return site


def create_access_token(site_tag: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=VARS["jwt_expiry_hours"])
    return jwt.encode(
        {"sub": site_tag, "exp": expires},
        VARS["jwt_secret"],
        algorithm="HS256",
    )


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, VARS["jwt_secret"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise fa.HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise fa.HTTPException(status_code=401, detail="Invalid token")

    tag: str | None = payload.get("sub")
    if tag is None:
        raise fa.HTTPException(status_code=401, detail="Invalid token")

    return tag


def create_reset_token(site_tag: str, password_db_hash: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=48)
    return jwt.encode(
        {
            "sub": site_tag,
            "purpose": "reset",
            "pfp": password_fingerprint(password_db_hash),
            "exp": expires,
        },
        VARS["jwt_secret"],
        algorithm="HS256",
    )


def decode_reset_token(token: str) -> tuple[str, str]:
    """Returns (site_tag, password_fingerprint)"""

    try:
        payload = jwt.decode(token, VARS["jwt_secret"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise fa.HTTPException(status_code=400, detail="Reset link has expired")
    except jwt.InvalidTokenError:
        raise fa.HTTPException(status_code=400, detail="Invalid reset link")

    if payload.get("purpose") != "reset":
        raise fa.HTTPException(status_code=400, detail="Invalid reset link")

    tag = payload.get("sub")
    pfp = payload.get("pfp")
    if tag is None or pfp is None:
        raise fa.HTTPException(status_code=400, detail="Invalid reset link")

    return tag, pfp


def create_email_change_token(site_tag: str, new_email: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=48)
    return jwt.encode(
        {
            "sub": site_tag,
            "purpose": "email_change",
            "new_email": new_email,
            "exp": expires,
        },
        VARS["jwt_secret"],
        algorithm="HS256",
    )


def decode_email_change_token(token: str) -> tuple[str, str]:
    """Returns (site_tag, new_email)"""

    try:
        payload = jwt.decode(token, VARS["jwt_secret"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise fa.HTTPException(status_code=400, detail="Confirmation link has expired")
    except jwt.InvalidTokenError:
        raise fa.HTTPException(status_code=400, detail="Invalid confirmation link")

    if payload.get("purpose") != "email_change":
        raise fa.HTTPException(status_code=400, detail="Invalid confirmation link")

    tag = payload.get("sub")
    new_email = payload.get("new_email")
    if tag is None or new_email is None:
        raise fa.HTTPException(status_code=400, detail="Invalid confirmation link")

    return tag, new_email


def create_download_token(site_tag: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=1)
    return jwt.encode(
        {"sub": site_tag, "purpose": "download", "exp": expires},
        VARS["jwt_secret"],
        algorithm="HS256",
    )


def decode_download_token(token: str) -> str:
    """Returns site_tag"""

    try:
        payload = jwt.decode(token, VARS["jwt_secret"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise fa.HTTPException(status_code=400, detail="Download link has expired")
    except jwt.InvalidTokenError:
        raise fa.HTTPException(status_code=400, detail="Invalid download link")

    if payload.get("purpose") != "download":
        raise fa.HTTPException(status_code=400, detail="Invalid download link")

    tag = payload.get("sub")
    if tag is None:
        raise fa.HTTPException(status_code=400, detail="Invalid download link")

    return tag


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def password_fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]
