from datetime import datetime

from database.models import Site


def test_site_get_parent_domain_2_levels():
    site = Site(id="test.com", hostname="test.com", admin_password="test")
    assert site.get_parent_domain() == "test.com"


def test_site_get_parent_domain_3_levels():
    site = Site(id="sub.test.com", hostname="sub.test.com", admin_password="test")
    assert site.get_parent_domain() == "test.com"


def test_site_get_parent_domain_4_levels():
    site = Site(
        id="foo.sub.test.com", hostname="foo.sub.test.com", admin_password="test"
    )
    assert site.get_parent_domain() == "test.com"


def test_site_is_donor():
    site = Site(id="test.com", hostname="test.com", admin_password="test")
    assert site.is_donor() is False


def test_site_donor():
    site = Site(
        id="test.com", hostname="test.com", admin_password="test", donated_amount=7
    )
    assert site.is_donor() is True
    assert site.has_perks() is True

    site.donated_amount = 6.99
    assert site.has_perks() is False

    site.donated_amount = 0
    assert site.is_donor() is False
    assert site.has_perks() is False


def test_is_installed():
    site = Site(id="test.com", hostname="test.com", admin_password="test")
    assert site.is_installed() is False

    site.installed_at = datetime.now()
    assert site.is_installed() is True
