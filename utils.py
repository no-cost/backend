import secrets


def random_string(*args, **kwargs) -> str:
    return secrets.token_urlsafe(*args, **kwargs)
