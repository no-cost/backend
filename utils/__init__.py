import re
import secrets

from utils.cmd import run_cmd
from utils.mail import send_mail
from utils.turnstile import verify_turnstile

__all__ = ["run_cmd", "send_mail", "verify_turnstile", "random_string", "validate_tag"]

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
