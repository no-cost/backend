import argparse
import asyncio
import sys

from database.models import Site
from database.session import async_session_factory, engine
from site_manager import backup_site as do_backup


async def _main():
    parser = argparse.ArgumentParser(description="Backup tenant site(s)")
    parser.add_argument(
        "identifier",
        nargs="?",
        help="Site tag, admin email, or hostname (omit to backup all active sites)",
    )
    parser.add_argument(
        "--periodic",
        action="store_true",
        help="Use periodic (date-stamped) backup location instead of attic",
        default=True,
    )
    parser.add_argument(
        "--delete-older-than",
        type=int,
        default=7,
        help="Delete periodic backups older than N days (default: 7, negative to disable)",
    )

    args = parser.parse_args()

    try:
        async with async_session_factory() as db:
            if args.identifier:
                site = await Site.get_by_identifier(db, args.identifier)
                if site is None:
                    print(
                        f"Error: active site '{args.identifier}' not found",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                sites = [site]
            else:
                sites = [site async for site in Site.get_all_active(db)]
                if not sites:
                    print("No active sites found", file=sys.stderr)
                    sys.exit(1)

        for site in sites:
            try:
                print(f"Backing up site: {site.tag}")
                runner = do_backup(
                    site,
                    periodic=args.periodic,
                    delete_older_than_days=args.delete_older_than,
                )
                print(runner.stdout.read())
                print(runner.stderr.read())
                print(f"Site backed up: {site.tag}")
            except RuntimeError as e:
                print(f"Failed to backup {site.tag}: {e}", file=sys.stderr)
    finally:
        await engine.dispose()


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
