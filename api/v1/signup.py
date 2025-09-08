import typing as t

import fastapi as fa
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session
from database.models import Site

V1_SIGNUP = fa.APIRouter(prefix="/signup")


class SignupRequest(BaseModel):
    email: str
    password: str
    site_type: str
    site_tag: str
    parent_domain: str


@V1_SIGNUP.post("/")
async def signup(
    request: SignupRequest, db: t.Annotated[AsyncSession, fa.Depends(get_session)]
):
    """
    Create a new site.
    """

    # TODO: validate hostname, site type, check tag blacklist etc.
    # TODO: hash password

    hostname = f"{request.site_tag}.{request.parent_domain}"
    site = Site(
        admin_email=request.email,
        admin_password=request.password,
        site_type=request.site_type,
        hostname=hostname,
    )

    # TODO: setup site, send welcome email in bg

    db.add(site)
    await db.commit()

    return {"message": "Site created successfully"}
