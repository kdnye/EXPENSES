from server_config import resolve_secret_value


def test_resolve_secret_value_prefers_plain_env(monkeypatch):
    monkeypatch.setenv("NETSUITE_SFTP_PASSWORD", "local-secret")
    monkeypatch.delenv("NETSUITE_SFTP_PASSWORD_SECRET", raising=False)

    assert (
        resolve_secret_value("NETSUITE_SFTP_PASSWORD", "NETSUITE_SFTP_PASSWORD_SECRET")
        == "local-secret"
    )
