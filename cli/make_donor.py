import argparse
import asyncio
import sys

from database.models import Site
from database.session import async_session_factory, engine
from site_manager.tenant_config import update_config
from utils.mail import send_donor_thank_you


async def _main():
    parser = argparse.ArgumentParser(description="Set donated amount for a tenant site")
    parser.add_argument("identifier", help="Site tag, admin email, or hostname")
    parser.add_argument("amount", type=float, help="Donated amount in EUR")

    args = parser.parse_args()

    try:
        async with async_session_factory() as db:
            site = await Site.get_by_identifier(db, args.identifier)

            if site is None:
                sys.exit(f"Error: active site '{args.identifier}' not found")

            site.donated_amount = (site.donated_amount or 0.0) + args.amount
            await db.commit()

            await update_config(site, {"donated_amount": site.donated_amount})

            if args.amount > 0:
                print(f"Sending thank you email to {site.admin_email}")
                send_donor_thank_you(
                    to=site.admin_email,
                    amount=f"{args.amount:.2f}",
                    currency="EUR",
                    total=site.donated_amount,
                    has_perks=site.has_donor_perks(),
                )

        print(f"donated_amount={site.donated_amount} for site '{site.tag}'")
    finally:
        await engine.dispose()


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
