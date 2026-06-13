"""B1 — admin auth must fail CLOSED on weak/unset passwords.

These tests pin the security guarantee that the historical "admin/admin123"
default (and any empty/placeholder/too-short password) can NEVER unlock the
admin surface. Only a strong, explicitly-configured password is accepted.
"""

import pytest

from app import config


@pytest.mark.parametrize(
    "pw",
    ["", "admin123", "admin", "password", "changeme", "short", "Sh0rt!"],
)
def test_insecure_passwords_are_rejected(monkeypatch, pw):
    monkeypatch.setattr(config.settings, "ADMIN_PASSWORD", pw)
    assert config.admin_password_is_secure() is False


@pytest.mark.parametrize(
    "pw",
    ["xYiJyQEngjiVX6eojO7_zZBRF1tGzQzz", "a-very-strong-passphrase-2026"],
)
def test_strong_passwords_are_accepted(monkeypatch, pw):
    monkeypatch.setattr(config.settings, "ADMIN_PASSWORD", pw)
    assert config.admin_password_is_secure() is True


def test_default_config_ships_with_no_usable_password():
    # The shipped default must itself be insecure (fail-closed by default).
    fresh = config.Settings(_env_file=None)
    monkeypatched = config.settings.ADMIN_PASSWORD
    try:
        config.settings.ADMIN_PASSWORD = fresh.ADMIN_PASSWORD
        assert config.admin_password_is_secure() is False
    finally:
        config.settings.ADMIN_PASSWORD = monkeypatched
