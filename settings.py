from os import getenv
from pathlib import Path


class Settings:
    """
    Settings for the service.
    """

    AVAILABLE_SITE_TYPES = [
        "flarum",
        # "wordpress",
    ]
    """The site types that are available to be created."""

    DATABASE_URL = getenv("DATABASE_URL", "sqlite:///database.sqlite")
    """The database URL to use for the service."""

    PERKS_DONATION_AMOUNT = 7
    """The amount of donations required to have perks (such as the footer removed)."""

    CHROOT_SYSTEM_HARDLINKS = {
        path: path
        for path in [
            Path("/lib/x86_64-linux-gnu/libssl.so.1.1"),
            Path("/lib/x86_64-linux-gnu/libcrypto.so.1.1"),
        ]
    }
    """A list of paths to system files to hardlink to the chroot directory."""
