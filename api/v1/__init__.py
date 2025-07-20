import fastapi as fa
from fastapi import Depends

from api.v1.account import V1_ACCOUNT
from api.v1.signup import V1_SIGNUP
from database.session import get_session, AsyncSessionContext
from database.models import Site

V1 = fa.APIRouter(prefix="/v1")


# TODO: testovanie, odstranit


@V1.get("/")
async def index(db: AsyncSessionContext = Depends(get_session)):
    async with db as session:
        site = Site(
            id="world",
            hostname="test.com",
            admin_password="test",
            site_type="flarum",
            admin_email="test@test.com",
            chroot_dir="/tmp/test",
        )
        session.add(site)
        await session.commit()
        await session.refresh(
            site
        )  # pragma: no cover # TODO: why is this never caught in coverage?

    return {"message": f"hello {site.id}"}


V1.include_router(V1_ACCOUNT)
V1.include_router(V1_SIGNUP)
