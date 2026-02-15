import asyncio
import time

import httpx
import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database.models import Site
from settings import VARS
from tests.integration.conftest import INTEGRATION_TEST_TOKEN
from utils.auth import create_reset_token

TEST_PASSWORD = "TestPassword123!"
TEST_NEW_PASSWORD = "NewPassword456!"

INSTALL_TIMEOUT_S = 300
INSTALL_POLL_INTERVAL_S = 5


@pytest.fixture(params=VARS["available_site_types"], scope="class")
def site(request):
    site_type = request.param
    tag = _tag_for(site_type)

    asyncio.run(_delete_site_record(tag))

    state = {
        "tag": tag,
        "email": f"{tag}@example.com",
        "site_type": site_type,
    }

    yield state

    asyncio.run(_delete_site_record(tag))


class TestTenantLifecycle:
    def test_health_check(self, api, site):
        r = api.get("/v1/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_allowed_domains(self, api, site):
        r = api.get("/v1/signup/allowed-domains")
        assert r.status_code == 200
        domains = r.json()
        assert isinstance(domains, list)
        assert len(domains) > 0

    def test_signup(self, api, site):
        r = api.post(
            "/v1/signup/",
            json={
                "tag": site["tag"],
                "email": site["email"],
                "site_type": site["site_type"],
                "turnstile_token": "bypassed-by-x-token",
            },
            headers={"X-Test-Token": INTEGRATION_TEST_TOKEN},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["site_tag"] == site["tag"]
        assert site["tag"] in data["hostname"]
        site["hostname"] = data["hostname"]

    def test_set_password(self, api, site):
        db_site = asyncio.run(_get_site(site["tag"]))
        assert db_site is not None, "test site not found in DB after signup"

        token = create_reset_token(site["tag"], db_site.admin_password)
        r = api.post(
            "/v1/account/reset-password",
            json={"token": token, "password": TEST_PASSWORD},
        )
        assert r.status_code == 200, r.text

    def test_login(self, api, site):
        r = api.post(
            "/v1/account/login",
            data={"username": site["tag"], "password": TEST_PASSWORD},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "access_token" in data
        site["token"] = data["access_token"]

    def test_wait_for_installation(self, api, site):
        headers = {"Authorization": f"Bearer {site['token']}"}
        deadline = time.monotonic() + INSTALL_TIMEOUT_S
        while time.monotonic() < deadline:
            r = api.get("/v1/account/", headers=headers)
            assert r.status_code == 200
            if r.json().get("installed_at") is not None:
                return
            time.sleep(INSTALL_POLL_INTERVAL_S)

        pytest.fail(
            f"{site['site_type']} site not installed within {INSTALL_TIMEOUT_S}s"
        )

    def test_get_account(self, api, site):
        headers = {"Authorization": f"Bearer {site['token']}"}
        r = api.get("/v1/account/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["tag"] == site["tag"]
        assert data["admin_email"] == site["email"]
        assert data["site_type"] == site["site_type"]
        assert data["installed_at"] is not None

    def test_app_reachable(self, api, site):
        r = httpx.get(f"https://{site['hostname']}", verify=False, timeout=15)
        assert r.status_code == 200, f"{site['hostname']} returned {r.status_code}"

    def test_change_password(self, api, site):
        r = api.post(
            "/v1/account/change-password",
            json={
                "old_password": TEST_PASSWORD,
                "new_password": TEST_NEW_PASSWORD,
            },
            headers={"Authorization": f"Bearer {site['token']}"},
        )
        assert r.status_code == 200, r.text

    def test_login_with_new_password(self, api, site):
        r = api.post(
            "/v1/account/login",
            data={"username": site["tag"], "password": TEST_NEW_PASSWORD},
        )
        assert r.status_code == 200, r.text
        site["token"] = r.json()["access_token"]

    def test_change_parent_domain(self, api, site):
        domains = site.get("domains", [])
        if len(domains) < 2:
            pytest.skip("no domains to change to")

        r = api.patch(
            "/v1/settings/parent-domain",
            json={"parent_domain": domains[1]},
            headers={"Authorization": f"Bearer {site['token']}"},
        )
        assert r.status_code == 200, r.text

    def test_app_reachable_after_domain_change(self, api, site):
        r = api.get(
            "/v1/account/",
            headers={"Authorization": f"Bearer {site['token']}"},
        )
        hostname = r.json()["hostname"]
        site["hostname"] = hostname

        r = httpx.get(f"https://{hostname}", verify=False, timeout=15)
        assert r.status_code == 200, f"{hostname} returned {r.status_code}"

    def test_fixup(self, api, site):
        r = api.post(
            "/v1/settings/fixup",
            headers={"Authorization": f"Bearer {site['token']}"},
        )
        assert r.status_code == 200, r.text

    def test_delete_site(self, api, site):
        r = api.delete(
            "/v1/account/",
            headers={"Authorization": f"Bearer {site['token']}"},
        )
        assert r.status_code == 200, r.text


async def _get_site(tag: str) -> Site | None:
    engine = create_async_engine(VARS["database_url"])
    factory = async_sessionmaker[AsyncSession](engine)
    async with factory() as db:
        site = await db.get(Site, tag)
    await engine.dispose()
    return site


async def _delete_site_record(tag: str) -> None:
    engine = create_async_engine(VARS["database_url"])
    factory = async_sessionmaker[AsyncSession](engine)
    async with factory() as db:
        site = await db.get(Site, tag)
        if site is not None:
            await db.delete(site)
            await db.commit()
    await engine.dispose()


def _tag_for(site_type: str) -> str:
    return f"inttest_{site_type}"
