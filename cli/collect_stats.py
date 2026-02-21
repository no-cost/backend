import asyncio
import sys
from datetime import datetime
from pathlib import Path

import aiomysql

from database.models import Site, SiteStats
from database.session import async_session_factory, engine
from settings import VARS

TENANTS_ROOT = Path(VARS["paths"]["tenants"]["root"])

CONTENT_QUERIES: dict[str, str] = {
    "flarum": "SELECT COUNT(*) FROM posts",
    "mediawiki": "SELECT COUNT(*) FROM page WHERE page_namespace = 0",
    "wordpress": "SELECT COUNT(*) FROM wp_posts WHERE post_status = 'publish' AND post_type IN ('post', 'page')",
}

USER_QUERIES: dict[str, str] = {
    "flarum": "SELECT COUNT(*) FROM users",
    "mediawiki": "SELECT COUNT(*) FROM user",
    "wordpress": "SELECT COUNT(*) FROM wp_users",
}

# per-app upload directories (relative to tenant root)
UPLOAD_DIRS: dict[str, str] = {
    "flarum": "app/public/assets",
    "mediawiki": "app/public/images",
    "wordpress": "app/public/wp-content/uploads",
}


async def _query_tenant_db(tag: str, query: str) -> int:
    conn = await aiomysql.connect(
        unix_socket="/var/run/mysqld/mysqld.sock",
        db=f"tenant_{tag}",
        user="root",
    )
    try:
        async with conn.cursor() as cur:
            await cur.execute(query)
            row = await cur.fetchone()
            return row[0] if row else 0
    finally:
        conn.close()


def _get_upload_size_mb(tag: str, site_type: str) -> float:
    upload_dir = TENANTS_ROOT / tag / UPLOAD_DIRS.get(site_type, "")
    if not upload_dir.exists():
        return 0.0

    total = sum(f.stat().st_size for f in upload_dir.rglob("*") if f.is_file())
    return round(total / 1024 / 1024, 2)


async def _main():
    now = datetime.now()
    collected = 0
    errors = 0

    try:
        async with async_session_factory() as db:
            sites = [
                site async for site in Site.get_all_active(db) if site.is_installed()
            ]

            for site in sites:
                try:
                    content_query = CONTENT_QUERIES.get(site.site_type)
                    user_query = USER_QUERIES.get(site.site_type)

                    if not content_query or not user_query:
                        print(
                            f"skip {site.tag}: unknown site type '{site.site_type}'",
                            file=sys.stderr,
                        )
                        continue

                    content_count = await _query_tenant_db(site.tag, content_query)
                    user_count = await _query_tenant_db(site.tag, user_query)
                    assets_mb = _get_upload_size_mb(site.tag, site.site_type)

                    stats = SiteStats(
                        site_tag=site.tag,
                        content_count=content_count,
                        user_count=user_count,
                        assets_mb=assets_mb,
                        collected_at=now,
                    )
                    db.add(stats)
                    collected += 1

                    print(
                        f"{site.tag}: content={content_count} users={user_count} assets={assets_mb} MB"
                    )
                except Exception as e:
                    errors += 1
                    print(f"error {site.tag}: {e}", file=sys.stderr)

            await db.commit()
    finally:
        await engine.dispose()

    print(f"\ncollected stats for {collected} sites ({errors} errors)")


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
