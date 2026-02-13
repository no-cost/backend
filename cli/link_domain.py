import argparse
import asyncio
import sys

from database.models import Site
from database.session import async_session_factory, engine
from settings import VARS
from site_manager.custom_domains import (
    CNAMENotFoundError,
    DomainAlreadyLinkedError,
    link_custom_domain,
    unlink_custom_domain,
)


async def _main():
    parser = argparse.ArgumentParser(
        description="Link or change the domain for a tenant site"
    )
    parser.add_argument("hostname", help="Domain to link (custom or allowed)")
    parser.add_argument("identifier", help="Site tag, admin email, or hostname")

    args = parser.parse_args()
    hostname = args.hostname.lower().strip()

    try:
        async with async_session_factory() as db:
            site = await Site.get_by_identifier(db, args.identifier)

            if site is None:
                print(
                    f"Error: active site '{args.identifier}' not found", file=sys.stderr
                )
                sys.exit(1)

            parent = _extract_parent_domain(hostname)

            if parent is not None:
                # switching internal parent domain
                canonical = f"{site.tag}.{parent}"
                if site.hostname == canonical:
                    print(
                        f"Error: site is already using '{canonical}'", file=sys.stderr
                    )
                    sys.exit(1)
                await unlink_custom_domain(db, site, canonical)
                print(f"Domain changed to '{canonical}' for site '{site.tag}'")
            else:
                # custom/user domain
                await link_custom_domain(db, site, hostname)
                print(f"Custom domain '{hostname}' linked to site '{site.tag}'")
    except DomainAlreadyLinkedError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except CNAMENotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await engine.dispose()


def _extract_parent_domain(hostname: str) -> str | None:
    for domain in VARS["allowed_domains"]:
        if hostname == domain or hostname.endswith(f".{domain}"):
            return domain
    return None


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
