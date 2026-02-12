import re
import secrets
from pathlib import Path

from settings import VARS
from utils.cmd import run_cmd
from utils.ip import get_client_ip
from utils.mail import send_mail
from utils.turnstile import verify_turnstile

__all__ = [
    "run_cmd",
    "send_mail",
    "verify_turnstile",
    "random_string",
    "validate_tag",
    "get_client_ip",
    "get_attic_backup_path",
    "get_latest_host_backup",
]

TAG_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def random_string(*args, **kwargs) -> str:
    return secrets.token_urlsafe(*args, **kwargs)


def validate_tag(tag: str) -> str:
    if len(tag) > 32:
        raise ValueError("Tag must be less than 32 characters.")
    if len(tag) < 3:
        raise ValueError("Tag must be at least 3 characters.")
    if not TAG_PATTERN.match(tag):
        raise ValueError("Tag must contain only letters, digits, and underscores.")
    return tag


def get_attic_backup_path(tag: str) -> Path:
    return Path(VARS["paths"]["backup_attic_root"]) / f"{tag}.tar.gz"


def get_latest_host_backup(tag: str) -> Path | None:
    backup_dir = Path(VARS["paths"]["backup_host_root"]) / tag
    if not backup_dir.is_dir():
        return None

    archives = sorted(backup_dir.glob("*.tar.gz"), reverse=True)
    return archives[0] if archives else None
