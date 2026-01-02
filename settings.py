from os import getenv


class Settings:
    """
    Settings for the service.
    """

    AVAILABLE_SITE_TYPES = [
        "flarum",
        "wordpress",
        "mediawiki",
    ]
    """The site types that are available to be created."""

    ALLOWED_DOMAINS = getenv(
        "ALLOWED_DOMAINS", "no-cost.site,no-cost.forum,no-cost.wiki"
    ).split(",")
    """The domains allowed for site creation (user chooses on signup)."""

    DATABASE_URL = getenv("DATABASE_URL", "sqlite:///database.sqlite")
    """The database URL to use for the service."""

    ENVIRONMENT = getenv("ENVIRONMENT", "dev")
    """The environment (dev or prod)."""

    PERKS_DONATION_AMOUNT = 7
    """The amount of donations required to have perks (such as the footer removed)."""
