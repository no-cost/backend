import pytest

from database.models import Site


@pytest.mark.asyncio
async def test_db_exception(test_db_session):
    async with test_db_session as session:
        site = Site(
            hostname="testid.com",
            admin_password="test",
            site_type="flarum",
            admin_email="id@test.com",
            chroot_dir="/tmp/id",
        )
        session.add(site)

        await session.commit()
        await session.refresh(site)

        assert len(site.id) == 4
