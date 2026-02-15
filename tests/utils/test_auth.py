import bcrypt

from utils.auth import password_fingerprint, verify_password


def test_verify_password_correct():
    password = "test_password"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    hashed = bcrypt.hashpw(b"correct_password", bcrypt.gensalt()).decode()
    assert verify_password("wrong_password", hashed) is False


def test_password_fingerprint_consistent():
    assert password_fingerprint("$2b$12$blabla") == password_fingerprint(
        "$2b$12$blabla"
    )


def test_password_fingerprint_different_hashes():
    assert password_fingerprint("$2b$12$blabla") != password_fingerprint("$2b$12$foobar")


def test_password_fingerprint_length():
    fp = password_fingerprint("$2b$12$blablablablablablablablablablablabla")
    assert len(fp) == 16
