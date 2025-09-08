import pytest
from sqlalchemy.exc import IntegrityError

from database.models import Site


@pytest.mark.asyncio
async def test_db_exception(test_db_session):
    with pytest.raises(IntegrityError):
        async with test_db_session as session:
            session.add(
                Site(
                    id="abc",
                    hostname="testabc.com",
                    admin_password="test",
                    site_type="flarum",
                    admin_email="abc@test.com",
                    chroot_dir="/tmp/abc",
                )
            )
            await session.commit()

            session.add(
                Site(
                    id="abc",  # same id
                    hostname="testdef.com",
                    admin_password="test",
                    site_type="flarum",
                    admin_email="def@test.com",
                    chroot_dir="/tmp/def",
                )
            )
            await session.commit()  # IntegrityError
