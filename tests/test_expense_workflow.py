from server_config import resolve_debug_flag, resolve_port


def test_resolve_port_uses_default_for_invalid_value(monkeypatch):
    monkeypatch.setenv("PORT", "abc")
    assert resolve_port() == 5000


def test_resolve_debug_flag_understands_truthy_values(monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "yes")
    assert resolve_debug_flag() is True
