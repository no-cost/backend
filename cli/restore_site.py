import argparse
import asyncio
import sys

from database.models import Site
from database.session import async_session_factory, engine
from site_manager import restore_site as do_restore


async def _main():
    parser = argparse.ArgumentParser(description="Restore a tenant site from backup")
    parser.add_argument("identifier", help="Site tag, admin email, or hostname")
    parser.add_argument(
        "--from",
        dest="backup_mode",
        choices=["attic", "periodic"],
        default="attic",
        help="Backup source: attic (default) or periodic",
    )
    parser.add_argument(
        "--date",
        help="Backup date (YYYY-MM-DD), required for periodic restores",
    )

    args = parser.parse_args()

    if args.backup_mode == "periodic" and not args.date:
        print("Error: --date is required for periodic restores", file=sys.stderr)
        sys.exit(1)

    try:
        async with async_session_factory() as db:
            site = await Site.get_by_identifier(db, args.identifier)

            if site is None:
                print(
                    f"Error: active site '{args.identifier}' not found", file=sys.stderr
                )
                sys.exit(1)

        runner = do_restore(
            site,
            backup_mode=args.backup_mode,
            backup_date=args.date,
        )
        print(runner.stdout.read())
        print(runner.stderr.read())
        print(f"Site restored: {site.tag}")
    finally:
        await engine.dispose()


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
