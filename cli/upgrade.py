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
        "-s",
        help="Upgrade all tenants of this service type",
        choices=["flarum", "mediawiki", "wordpress"],
        default=None,
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
                await upgrade_site(site)
                print(f"ok {site.tag}")
    finally:
        await engine.dispose()


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
