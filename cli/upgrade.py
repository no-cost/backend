import argparse
import asyncio

from database.models import Site
from database.session import async_session_factory
from site_manager import upgrade_site


async def _main():
    parser = argparse.ArgumentParser(description="Upgrade tenant sites")
    parser.add_argument("--tag", help="Tenant to upgrade")
    parser.add_argument(
        "--service", "-s",
        help="Upgrade all tenants of this service type",
        choices=["flarum", "mediawiki", "wordpress"],
        default=None,
    )

    args = parser.parse_args()

    async with async_session_factory() as db:
        async for site in Site.get_all_active(
            db,
            (Site.site_type == args.service) if args.service else None,
            (Site.tag == args.tag) if args.tag else None,
        ):
            print(f"Upgrading {site.tag} ({site.site_type})...")
            await upgrade_site(site)
            print(f"ok {site.tag}")


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
