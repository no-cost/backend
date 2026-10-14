import argparse
import asyncio
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from database.models import Site
from database.session import async_session_factory, engine
from site_manager import backup_site as do_backup
from utils.priority import lower_priority


def _backup(site: Site, periodic: bool, delete_older_than_days: int) -> float:
    started = time.monotonic()
    do_backup(site, periodic=periodic, delete_older_than_days=delete_older_than_days)
    return time.monotonic() - started


async def _main():
    parser = argparse.ArgumentParser(description="Backup tenant site(s)")
    parser.add_argument(
        "identifier",
        nargs="?",
        help="Site tag, admin email, or hostname (omit to backup all active sites)",
    )
    parser.add_argument(
        "--no-periodic",
        action="store_true",
        help="Use attic backup location instead of periodic (date-stamped)",
        default=False,
    )
    parser.add_argument(
        "--delete-older-than",
        type=int,
        default=7,
        help="Delete periodic backups older than N days (default: 7, negative to disable)",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="Sites backed up in parallel (default: 4)",
    )

    args = parser.parse_args()

    # backups (and everything they spawn) only get CPU and disk time the sites don't need
    lower_priority()

    try:
        async with async_session_factory() as db:
            if args.identifier:
                site = await Site.get_by_identifier(db, args.identifier)
                if site is None:
                    sys.exit(f"Error: active site '{args.identifier}' not found")
                sites = [site]
            else:
                sites = [site async for site in Site.get_all_active(db)]
                if not sites:
                    sys.exit("No active sites found")
    finally:
        await engine.dispose()

    failed = 0
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {
            pool.submit(
                _backup, site, not args.no_periodic, args.delete_older_than
            ): site
            for site in sites
        }
        for future in as_completed(futures):
            site = futures[future]
            try:
                print(f"Site backed up: {site.tag} ({future.result():.1f}s)", flush=True)
            except RuntimeError as e:
                failed += 1
                print(f"Failed to backup {site.tag}: {e}", file=sys.stderr, flush=True)

    print(f"Backed up {len(sites) - failed} of {len(sites)} sites, {failed} failed")
    if failed:
        sys.exit(1)


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
