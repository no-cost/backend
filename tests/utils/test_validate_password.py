import pytest

from utils import validate_password


def test_valid_password():
    assert validate_password("jankomarienka1!") == "jankomarienka1!"


def test_password_too_short():
    with pytest.raises(ValueError, match="at least 8"):
        validate_password("abc1234")


def test_password_no_digit():
    with pytest.raises(ValueError, match="at least one number"):
        validate_password("abcdefgh")


def test_password_min_length_with_digit():
    assert validate_password("abcdefg1") == "abcdefg1"
