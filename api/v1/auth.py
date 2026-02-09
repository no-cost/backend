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
    """Dependency that extracts the JWT, validates it, and returns the Site."""

    try:
        payload = jwt.decode(token, VARS["jwt_secret"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise fa.HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise fa.HTTPException(status_code=401, detail="Invalid token")

    tag: str | None = payload.get("sub")
    if tag is None:
        raise fa.HTTPException(status_code=401, detail="Invalid token")

    site = await db.execute(
        select(Site).where(Site.tag == tag, Site.removed_at.is_(None))
    )
    site = site.scalar_one_or_none()

    if site is None:
        raise fa.HTTPException(status_code=401, detail="Site not found")

    return site


def create_access_token(site_tag: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=VARS["jwt_expiry_hours"])
    return jwt.encode(
        {"sub": site_tag, "exp": expires},
        VARS["jwt_secret"],
        algorithm="HS256",
    )


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
