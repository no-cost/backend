import argparse
import asyncio
import sys

from sqlalchemy import select

from database.models import Site
from database.session import async_session_factory
from site_manager import backup_site as do_backup


async def _main():
    parser = argparse.ArgumentParser(description="Backup a tenant site")
    parser.add_argument("tag", help="Unique identifier for the site")

    args = parser.parse_args()

    async with async_session_factory() as db:
        result = await db.execute(
            select(Site).where(Site.tag == args.tag, Site.removed_at.is_(None))
        )
        site = result.scalar_one_or_none()

        if site is None:
            print(f"Error: active site '{args.tag}' not found", file=sys.stderr)
            sys.exit(1)

    do_backup(site, site.site_type)
    print(f"Site backed up: {args.tag}")


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
