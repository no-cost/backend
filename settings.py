"""
Interface for getting settings from environment variables.
"""

from os import environ

allowed_domains = environ["ALLOWED_DOMAINS"].split(",")

VARS = {
    "allowed_domains": allowed_domains,
    "available_site_types": ["flarum", "mediawiki", "wordpress"],
    "database_url": environ["DATABASE_URL"],
    "jwt_secret": environ["JWT_SECRET"],
    "jwt_expiry_hours": 24,
    "main_domain": allowed_domains[0],
    "php_version": environ["PHP_VERSION"],
    "paths": {
        "tenants": {
            "root": environ["TENANTS_ROOT"],
            "skeleton_root": environ["SKELETON_ROOT"],
        },
        "backup_host_root": environ["BACKUP_HOST_ROOT"],
        "backup_attic_root": environ["BACKUP_ATTIC_ROOT"],
    },
}
