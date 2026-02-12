import argparse
import asyncio
import sys
from datetime import datetime

import bcrypt
from sqlalchemy.exc import IntegrityError

from database.models import Site
from database.session import async_session_factory, engine
from settings import VARS
from site_manager import provision_site
from site_manager.custom_domains import write_nginx_maps
from utils import random_string, validate_tag
from utils.auth import create_reset_token


async def _main():
    parser = argparse.ArgumentParser(description="Create a new tenant site")
    parser.add_argument("tag", help="Unique tenant identifier")
    parser.add_argument(
        "service_type",
        choices=["flarum", "mediawiki", "wordpress"],
        help="Type of site to create",
    )
    parser.add_argument("admin_email", help="Administrator email address")
    parser.add_argument(
        "--password",
        help="Admin password (generated if not provided)",
        default=None,
    )
    parser.add_argument(
        "--domain",
        help=f"Parent domain (default: {VARS['main_domain']})",
        default=VARS["main_domain"],
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force provisioning even if site already exists",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send welcome email with password reset link to admin email",
        default=True,
    )

    args = parser.parse_args()

    try:
        args.tag = validate_tag(args.tag)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    password = args.password or random_string(16)
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    hostname = f"{args.tag}.{args.domain}"

    try:
        async with async_session_factory() as db:
            site = Site(
                tag=args.tag,
                admin_email=args.admin_email,
                admin_password=hashed,
                site_type=args.service_type,
                hostname=hostname,
            )

            try:
                db.add(site)
                await db.commit()
            except IntegrityError:
                print(f"Error: site '{args.tag}' already exists", file=sys.stderr)
                sys.exit(1)

            reset_token = create_reset_token(site.tag, site.admin_password)
            runner = provision_site(
                site, reset_token, force=args.force, send_email=args.send_email
            )
            print(runner.stdout.read())
            print(runner.stderr.read())

            site.installed_at = datetime.now()
            await db.commit()

            await write_nginx_maps(db)

        print(f"Site created: {args.tag} ({hostname})")
        if not args.password:
            print(f"Generated admin password: {password}")
    finally:
        await engine.dispose()


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
