import re
import secrets

from settings import BLACKLISTED_TAGS

TAG_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")
INTTEST_TAG_PREFIX = "inttest_"


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


def is_tag_blacklisted(tag: str) -> bool:
    return tag in BLACKLISTED_TAGS or tag.startswith(INTTEST_TAG_PREFIX)
