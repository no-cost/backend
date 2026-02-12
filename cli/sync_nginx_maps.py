import asyncio

from database.session import async_session_factory, engine
from site_manager.custom_domains import write_nginx_maps


async def _main():
    try:
        async with async_session_factory() as db:
            await write_nginx_maps(db)
        print("Nginx maps synced and nginx reloaded")
    finally:
        await engine.dispose()


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
