import pytest

from utils import is_tag_blacklisted, validate_tag


def test_valid_tag():
    assert validate_tag("mysite") == "mysite"


def test_valid_tag_with_underscores():
    assert validate_tag("my_site_123") == "my_site_123"


def test_tag_min_length():
    assert validate_tag("abc") == "abc"


def test_tag_max_length():
    assert validate_tag("a" * 32) == "a" * 32


def test_tag_too_short():
    with pytest.raises(ValueError, match="at least 3"):
        validate_tag("ab")


def test_tag_too_long():
    with pytest.raises(ValueError, match="less than 32"):
        validate_tag("a" * 33)


def test_tag_invalid_characters():
    for tag in ["my-site", "my site", "my.site"]:
        with pytest.raises(ValueError, match="letters, digits, and underscores"):
            validate_tag(tag)


def test_tag_blacklisted():
    for tag in ["api", "www", "inttest_anything"]:
        assert is_tag_blacklisted(tag) is True


def test_not_blacklisted():
    assert is_tag_blacklisted("mysite") is False
    assert is_tag_blacklisted("cool_forum") is False
