import argparse
import asyncio
import sys
from datetime import datetime

from database.models import Site
from database.session import async_session_factory
from site_manager import remove_site as do_remove
from site_manager.custom_domains import write_nginx_maps


async def _main():
    parser = argparse.ArgumentParser(description="Remove a tenant site")
    parser.add_argument("identifier", help="Site tag, admin email, or hostname")
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup before removal (for GDPR full deletion)",
    )

    args = parser.parse_args()

    async with async_session_factory() as db:
        site = await Site.get_by_identifier(db, args.identifier)

        if site is None:
            print(f"Error: active site '{args.identifier}' not found", file=sys.stderr)
            sys.exit(1)

        do_remove(site, skip_backup=args.skip_backup)

        site.removed_at = datetime.now()
        site.removal_reason = "Removed via CLI"
        await db.commit()

        await write_nginx_maps(db)

    print(f"Site removed: {site.tag}")


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
