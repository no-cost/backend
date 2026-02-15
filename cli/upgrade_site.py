import argparse
import asyncio

from database.models import Site
from database.session import async_session_factory, engine
from site_manager import upgrade_site


async def _main():
    parser = argparse.ArgumentParser(description="Upgrade tenant sites")
    parser.add_argument("--tag", help="Tenant to upgrade")
    parser.add_argument(
        "--service",
        help="Upgrade all tenants of this service type",
        choices=["flarum", "mediawiki", "wordpress"],
        default=None,
    )
    parser.add_argument(
        "--sync-files",
        "-s",
        help="Re-sync file structure from skeleton before upgrading",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()

    filters = []
    if args.service:
        filters.append(Site.site_type == args.service)
    if args.tag:
        filters.append(Site.tag == args.tag)

    try:
        async with async_session_factory() as db:
            async for site in Site.get_all_active(db, *filters):
                print(f"Upgrading {site.tag} ({site.site_type})...")
                result = await upgrade_site(site, sync_files=args.sync_files)
                if result is not None:
                    print(result.stdout.read())
                    print(result.stderr.read())
                print(f"ok {site.tag}")
    finally:
        await engine.dispose()


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
