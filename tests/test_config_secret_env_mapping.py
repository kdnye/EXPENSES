"""Tests for secret-backed environment variable mappings in ``config.Config``."""

import importlib

import config as config_module


def _reload_config_module():
    """Reload and return ``config`` after monkeypatched environment updates.

    Inputs:
        None. Reads process environment configured by ``monkeypatch`` in tests.

    Outputs:
        The reloaded ``config`` module object so callers can inspect
        ``config.Config`` values.

    External dependencies:
        Calls :func:`importlib.reload` to refresh module-level configuration.
    """

    return importlib.reload(config_module)


def test_oidc_values_can_be_read_from_direct_secret_env(monkeypatch):
    """Ensure OIDC values map from env vars used for Secret Manager injection.

    Inputs:
        monkeypatch: pytest fixture used to set environment variables.

    Outputs:
        None. Asserts expected values on ``Config`` attributes.

    External dependencies:
        Reloads ``config`` via helper ``_reload_config_module``.
    """

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@db:5432/app")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id-from-secret")
    monkeypatch.setenv("OIDC_ISSUER", "https://issuer.example.com")
    monkeypatch.setenv("OIDC_AUDIENCE", "audience-a,audience-b")

    config = _reload_config_module()

    assert config.Config.OIDC_CLIENT_ID == "client-id-from-secret"
    assert config.Config.OIDC_ISSUER == "https://issuer.example.com"
    assert config.Config.OIDC_AUDIENCE == ("audience-a", "audience-b")


def test_netsuite_key_material_can_be_read_from_secret_env(monkeypatch):
    """Ensure NetSuite key credentials use the expected environment variables.

    Inputs:
        monkeypatch: pytest fixture used to set environment variables.

    Outputs:
        None. Asserts key and passphrase values are exposed on ``Config``.

    External dependencies:
        Reloads ``config`` via helper ``_reload_config_module``.
    """

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@db:5432/app")
    monkeypatch.setenv("NETSUITE_SFTP_PRIVATE_KEY", "private-key-bytes")
    monkeypatch.setenv("NETSUITE_SFTP_PRIVATE_KEY_PASSPHRASE", "key-passphrase")

    config = _reload_config_module()

    assert config.Config.NETSUITE_SFTP_PRIVATE_KEY == "private-key-bytes"
    assert config.Config.NETSUITE_SFTP_PRIVATE_KEY_PASSPHRASE == "key-passphrase"
