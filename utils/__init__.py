import secrets

from utils.cmd import run_cmd
from utils.mail import send_mail
from utils.turnstile import verify_turnstile

__all__ = ["run_cmd", "send_mail", "verify_turnstile", "random_string"]


def random_string(*args, **kwargs) -> str:
    return secrets.token_urlsafe(*args, **kwargs)
