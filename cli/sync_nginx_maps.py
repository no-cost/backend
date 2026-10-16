import asyncio

from database.session import async_session_factory, engine
from site_manager.custom_domains import write_nginx_maps
from utils.sentry import init_sentry


async def _main():
    try:
        async with async_session_factory() as db:
            await write_nginx_maps(db)
        print("Nginx maps synced and nginx reloaded")
    finally:
        await engine.dispose()


def main():
    init_sentry("sync_nginx_maps")
    asyncio.run(_main())


if __name__ == "__main__":
    main()
