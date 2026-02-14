"""
Interface for getting settings from environment variables.
"""

from os import environ

allowed_domains = environ["ALLOWED_DOMAINS"].split(",")

# leaf keys must be strings, or else ansible_runner can't serialize them
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
            "root": environ["TENANTS_ROOT"],
            "skeleton_root": environ["SKELETON_ROOT"],
        },
        "backup_system_root": environ["BACKUP_SYSTEM_ROOT"],
        "backup_host_root": environ["BACKUP_HOST_ROOT"],
        "backup_attic_root": environ["BACKUP_ATTIC_ROOT"],
    },
    "info_mail": environ["MAILTO"],
    "kofi_verification_token": environ["KOFI_VERIFICATION_TOKEN"],
    "health_check_token": environ["HEALTH_CHECK_TOKEN"],
}

BLACKLISTED_TAGS = ["api", "www", "mail", "cname", "status", "support"]
