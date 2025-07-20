"""
Generic utility functions.
"""

import random
import string


def random_id(length: int = 4) -> str:
    """
    Generate a random ID of a given length.
    """

    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
