"""
Interface for getting settings from environment variables.
"""

from os import environ
from pathlib import Path

allowed_domains = environ["ALLOWED_DOMAINS"].split(",")

VARS = {
    "allowed_domains": allowed_domains,
    "available_site_types": ["flarum", "mediawiki", "wordpress"],
    "database_url": environ["DATABASE_URL"],
    "jwt_secret": environ["JWT_SECRET"],
    "jwt_expiry_hours": 24,
    "main_domain": allowed_domains[0],
    "php_version": environ["PHP_VERSION"],
    "turnstile_key": environ["TURNSTILE_KEY"],
    "paths": {
        "tenants": {
            "root": Path(environ["TENANTS_ROOT"]),
            "skeleton_root": Path(environ["SKELETON_ROOT"]),
        },
        "backup_host_root": Path(environ["BACKUP_HOST_ROOT"]),
        "backup_attic_root": Path(environ["BACKUP_ATTIC_ROOT"]),
    },
}
