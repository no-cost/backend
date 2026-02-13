import argparse
import asyncio
import sys

from sqlalchemy import or_

from database.models import Site
from database.session import async_session_factory, engine
from utils import get_attic_backup_path, get_latest_host_backup
from utils.ip import get_country_code


async def _main():
    parser = argparse.ArgumentParser(
        description="List tenant sites with optional filters"
    )

    parser.add_argument("-t", "--type", dest="site_type", help="Filter by site type")

    status_group = parser.add_mutually_exclusive_group()
    status_group.add_argument(
        "--removed", action="store_true", help="Show only removed sites"
    )
    status_group.add_argument(
        "--active", action="store_true", help="Show only active sites"
    )

    parser.add_argument("--donors", action="store_true", help="Show only donors")
    parser.add_argument(
        "--not-installed",
        action="store_true",
        help="Show only sites that failed or haven't finished installing",
    )
    parser.add_argument("--email", help="Filter by admin email (substring match)")
    parser.add_argument(
        "--domain", help="Filter by hostname/parent domain (substring match)"
    )
    parser.add_argument(
        "--ip", help="Filter by IP (matches created_ip or last_login_ip)"
    )
    parser.add_argument("--country", help="Filter by country code (e.g. SK, US)")
    parser.add_argument(
        "--has-backup",
        action="store_true",
        help="Show only sites with an attic backup on disk",
    )
    parser.add_argument(
        "--check-backups",
        action="store_true",
        help="Add HAS_BACKUP column (attic backup existence)",
    )
    parser.add_argument(
        "--host-backups",
        action="store_true",
        help="Add LAST_BACKUP column (latest periodic backup date)",
    )

    args = parser.parse_args()

    sql_filters = []
    if args.site_type:
        sql_filters.append(Site.site_type == args.site_type)
    if args.donors:
        sql_filters.append(Site.donated_amount > 0)
    if args.not_installed:
        sql_filters.append(Site.installed_at.is_(None))
    if args.email:
        sql_filters.append(Site.admin_email.contains(args.email))
    if args.domain:
        sql_filters.append(Site.hostname.contains(args.domain))
    if args.ip:
        sql_filters.append(
            or_(Site.created_ip == args.ip, Site.last_login_ip == args.ip)
        )

    if args.removed:
        match_removed = True
        sql_filters.append(Site.removed_at.is_not(None))
    elif args.active:
        match_removed = False
    else:
        match_removed = True

    try:
        async with async_session_factory() as db:
            sites = [
                site
                async for site in Site.get_all_active(
                    db, *sql_filters, match_removed=match_removed
                )
            ]
    finally:
        await engine.dispose()

    # post-fetch filters
    if args.country:
        cc = args.country.upper()
        sites = [
            s
            for s in sites
            if (s.created_ip is not None and get_country_code(s.created_ip) == cc)
            or (s.last_login_ip is not None and get_country_code(s.last_login_ip) == cc)
        ]

    if args.has_backup:
        sites = [s for s in sites if get_attic_backup_path(s.tag).exists()]

    if not sites:
        sys.exit("No sites match the given filters.")

    # build table
    headers = ["TAG", "TYPE", "HOSTNAME", "EMAIL", "CREATED", "STATUS", "DONOR"]
    if args.check_backups:
        headers.append("HAS_BACKUP")
    if args.host_backups:
        headers.append("LAST_BACKUP")

    rows = []
    n_active = n_removed = n_not_installed = n_donors = 0
    for site in sites:
        status = _status(site)
        if status == "active":
            n_active += 1
        elif status == "removed":
            n_removed += 1
        if not site.is_installed():
            n_not_installed += 1
        if site.is_donor():
            n_donors += 1

        row = [
            site.tag,
            site.site_type,
            site.hostname,
            site.admin_email,
            site.created_at.strftime("%Y-%m-%d") if site.created_at else "-",
            status,
            f"{site.donated_amount:.2f} EUR" if site.is_donor() else "",
        ]

        if args.check_backups:
            row.append("yes" if get_attic_backup_path(site.tag).exists() else "no")
        if args.host_backups:
            latest = get_latest_host_backup(site.tag)
            row.append(latest.stem if latest else "-")

        rows.append(row)

    _print_table(headers, rows)

    parts = [f"{n_active} active", f"{n_removed} removed"]
    if n_not_installed:
        parts.append(f"{n_not_installed} not installed")
    parts.append(f"{n_donors} donors")
    print(f"\n{len(sites)} sites ({', '.join(parts)})")


def _status(site: Site) -> str:
    if site.removed_at:
        return "removed"
    if not site.is_installed():
        return "not installed"
    return "active"


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
