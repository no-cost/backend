import argparse
import asyncio
import sys

from database.models import Site
from database.session import async_session_factory, engine
from site_manager import backup_site as do_backup


async def _main():
    parser = argparse.ArgumentParser(description="Backup a tenant site")
    parser.add_argument("identifier", help="Site tag, admin email, or hostname")

    args = parser.parse_args()

    try:
        async with async_session_factory() as db:
            site = await Site.get_by_identifier(db, args.identifier)

            if site is None:
                print(f"Error: active site '{args.identifier}' not found", file=sys.stderr)
                sys.exit(1)

        runner = do_backup(site, site.site_type)
        print(runner.stdout.read())
        print(runner.stderr.read())
        print(f"Site backed up: {site.tag}")
    finally:
        await engine.dispose()


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
