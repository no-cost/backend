import asyncio
from pathlib import Path

from sqlalchemy import text

from database import models
from database.session import engine, get_session
from settings import Settings
from site_manager.flarum import install_flarum
from site_manager.wordpress import install_wordpress

type PathLinkDict = dict[Path, Path]
"""A dictionary that maps source (system) paths to destination (chroot) paths."""


async def install_site(site: models.Site):
    """
    Generic function to install a site with specific `Site.site_type`.
    Assumes that all sites are PHP applications.
    """

    await prepare_chroot(site)
    await create_user(site)

    match site.site_type:
        case "flarum":
            await install_flarum(site)
        case "wordpress":
            await install_wordpress(site)


async def prepare_chroot(site: models.Site):
    """
    Create (if it doesn't exist) & prepare the chroot directory for the PHP site.

    PHP applications and libraries require a few system libraries to be present in their chroot, otherwise
    they will not function properly. This also hardlinks the required system files from
    `Settings.CHROOT_SYSTEM_HARDLINKS` to the chroot directory.
    """

    await wait_exec("/usr/bin/mkdir", "-p", site.chroot_dir)
    await wait_exec("/usr/bin/chown", "-R", f"{site.id}:{site.id}", site.chroot_dir)
    await wait_exec("/usr/bin/chmod", "-R", "755", site.chroot_dir)

    # system, not site-specific links
    await prepare_hardlinks(site, Settings.CHROOT_SYSTEM_HARDLINKS)


async def prepare_hardlinks(site: models.Site, hardlinks: PathLinkDict):
    """
    Hardlink the given files to the chroot directory.
    """

    for src, dst in hardlinks.items():
        await wait_exec("/usr/bin/ln", "-f", str(src), str(site.chroot_dir / dst))


async def create_user(site: models.Site):
    """
    Create a new system user for the site.
    """

    await wait_exec(
        "/usr/sbin/useradd", "-m", "-s", "/usr/sbin/nologin", "-g", site.id, site.id
    )
    await wait_exec("/usr/sbin/groupadd", site.id)
    await wait_exec("/usr/sbin/usermod", "-a", "-G", site.id, site.id)
    await wait_exec("/usr/bin/passwd", "-dl", site.id)


async def create_database(site: models.Site):
    """
    Create a new MySQL database and user for a specific site.
    """

    if not engine.name.startswith("mysql"):
        raise ValueError("MySQL manager can only be used with MySQL databases.")

    identifier = f"site_{site.id}"

    async with get_session() as session:
        # CREATE DATABASE
        await session.execute(
            text(
                "CREATE DATABASE IF NOT EXISTS `:db_name` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            ).bindparams(db_name=identifier)
        )

        # CREATE USER
        await session.execute(
            text(
                "CREATE USER IF NOT EXISTS ':user_name'@'localhost' IDENTIFIED BY :password;"
            ).bindparams(user_name=identifier, password=site.admin_password),
        )

        # GRANT
        await session.execute(
            text(
                "GRANT ALL PRIVILEGES ON `:db_name`.* TO ':user_name'@'localhost';"
            ).bindparams(db_name=identifier, user_name=identifier)
        )
        await session.execute(text("FLUSH PRIVILEGES;"))


async def wait_exec(*cmd_args: str, **cmd_kwargs):
    """
    Wait for a command to finish executing and return the status code, stdout, and stderr.
    """

    process = await asyncio.create_subprocess_exec(
        *cmd_args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **cmd_kwargs,
    )
    stdout, stderr = await process.communicate()

    return process.returncode, stdout, stderr
