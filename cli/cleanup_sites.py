import argparse
import asyncio
import sys
from datetime import datetime, timedelta

from sqlalchemy import func, select

from database.models import Site, SiteStats
from database.session import async_session_factory, engine
from site_manager import remove_site as do_remove
from site_manager.custom_domains import write_nginx_maps

MIN_AGE_DAYS = 60

# too active
MAX_CONTENT = 10_000
MAX_USERS = 5_000
MAX_ASSETS_MB = 500

# inactive
MIN_CONTENT = 10
MIN_USERS = 2


def _classify(stats: SiteStats) -> str | None:
    if (
        stats.content_count > MAX_CONTENT
        or stats.user_count > MAX_USERS
        or stats.assets_mb > MAX_ASSETS_MB
    ):
        parts = []
        if stats.content_count > MAX_CONTENT:
            parts.append(f"content={stats.content_count}")
        if stats.user_count > MAX_USERS:
            parts.append(f"users={stats.user_count}")
        if stats.assets_mb > MAX_ASSETS_MB:
            parts.append(f"assets={stats.assets_mb}MB")
        return f"too active ({', '.join(parts)})"

    if stats.content_count < MIN_CONTENT or stats.user_count <= MIN_USERS:
        parts = []
        if stats.content_count < MIN_CONTENT:
            parts.append(f"content={stats.content_count}")
        if stats.user_count <= MIN_USERS:
            parts.append(f"users={stats.user_count}")
        return f"inactive ({', '.join(parts)})"

    return None


async def _get_latest_stats(db) -> dict[str, SiteStats]:
    latest_sub = (
        select(
            SiteStats.site_tag,
            func.max(SiteStats.collected_at).label("max_collected"),
        )
        .group_by(SiteStats.site_tag)
        .subquery()
    )

    stmt = select(SiteStats).join(
        latest_sub,
        (SiteStats.site_tag == latest_sub.c.site_tag)
        & (SiteStats.collected_at == latest_sub.c.max_collected),
    )

    result = await db.execute(stmt)
    return {row.site_tag: row for row in result.scalars()}


async def _main():
    parser = argparse.ArgumentParser(
        description="Clean up inactive or excessively active tenant sites"
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only show what would be removed (default: --dry-run)",
    )
    parser.add_argument(
        "-n",
        "--no-send-email",
        action="store_true",
        help="Do not send removal notification emails",
    )

    args = parser.parse_args()
    cutoff = datetime.now() - timedelta(days=MIN_AGE_DAYS)

    try:
        async with async_session_factory() as db:
            latest_stats = await _get_latest_stats(db)
            if not latest_stats:
                sys.exit("No stats collected yet. Run collect_stats first.")

            flagged: list[tuple[Site, str]] = []

            async for site in Site.get_all_active(db):
                if not site.is_installed():
                    continue
                if site.created_at > cutoff:
                    continue
                if site.has_donor_perks():
                    continue

                stats = latest_stats.get(site.tag)
                if stats is None:
                    continue

                reason = _classify(stats)
                if reason:
                    flagged.append((site, reason))

            if not flagged:
                print("No sites flagged for cleanup.")
                return

            # print summary table
            headers = [
                "TAG",
                "TYPE",
                "HOSTNAME",
                "CONTENT",
                "USERS",
                "ASSETS MB",
                "REASON",
            ]
            rows = []
            for site, reason in flagged:
                stats = latest_stats[site.tag]
                rows.append(
                    [
                        site.tag,
                        site.site_type,
                        site.hostname,
                        str(stats.content_count),
                        str(stats.user_count),
                        f"{stats.assets_mb:.1f}",
                        reason,
                    ]
                )

            _print_table(headers, rows)
            print(f"\n{len(flagged)} sites flagged for cleanup")

            if args.dry_run:
                print("(dry run — no changes made)")
                return

            for site, reason in flagged:
                try:
                    print(f"\nremoving {site.tag} ({reason})...")
                    runner = do_remove(
                        site,
                        send_email=not args.no_send_email,
                        reason=f"auto-cleanup: {reason}",
                    )
                    print(runner.stdout.read())
                    print(runner.stderr.read())

                    site.removed_at = datetime.now()
                    site.removal_reason = f"auto-cleanup: {reason}"
                    await db.commit()

                    print(f"removed {site.tag}")
                except Exception as e:
                    print(f"failed to remove {site.tag}: {e}", file=sys.stderr)

            await write_nginx_maps(db)
    finally:
        await engine.dispose()


def _print_table(headers: list[str], rows: list[list[str]]):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt.format(*row))


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
