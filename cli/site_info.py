import argparse
import asyncio
import sys

from database.models import Site
from database.session import async_session_factory, engine
from utils.ip import get_country_code


async def _main():
    parser = argparse.ArgumentParser(description="Display info about a tenant site")
    parser.add_argument("identifier", help="Site tag, admin email, or hostname")

    args = parser.parse_args()

    try:
        async with async_session_factory() as db:
            site = await Site.get_by_identifier(db, args.identifier)

            if site is None:
                print(
                    f"Error: active site '{args.identifier}' not found", file=sys.stderr
                )
                sys.exit(1)

        cc = get_country_code(site.created_ip) if site.created_ip else None

        print(f"tag:            {site.tag}")
        print(f"site_type:      {site.site_type}")
        print(f"hostname:       {site.hostname}")
        print(f"admin_email:    {site.admin_email}")
        print(f"installed:      {site.installed_at or 'not yet (or failed)'}")
        print(f"created_at:     {site.created_at}")
        print(f"created_ip:     {site.created_ip or 'N/A'}{f' ({cc})' if cc else ''}")
        print(
            f"last_login_ip:  {site.last_login_ip or 'N/A'}{f' ({cc})' if cc else ''}"
        )
        print(f"last_login_at:  {site.last_login_at or 'never'}")
        print(
            f"donor:          {f'yes ({site.donated_amount} EUR)' if site.is_donor() else 'no'}"
        )
        print(f"has_perks:      {'yes' if site.has_perks() else 'no'}")

        if site.removed_at:
            print(f"removed_at:     {site.removed_at}")
            print(f"removed_ip:     {site.removed_ip or 'N/A'}")
            print(f"removal_reason: {site.removal_reason or 'N/A'}")
    finally:
        await engine.dispose()


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
