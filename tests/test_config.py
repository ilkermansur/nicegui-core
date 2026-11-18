from ngui.config import LockEntry, home_from_env


def test_missing_config_returns_defaults(home):
    cfg = home.load_config()
    assert cfg.default_lang == "tr"
    assert cfg.roles["layout"] == "layout-sidebar"
    assert "store" in cfg.enabled


def test_config_roundtrip(home):
    cfg = home.load_config(); cfg.enabled.append("ai"); cfg.links["ai"] = "/x"
    home.save_config(cfg)
    again = home.load_config()
    assert again.enabled[-1] == "ai" and again.links == {"ai": "/x"}


def test_lock_roundtrip(home):
    home.save_lock({"ai": LockEntry("u", "c2", "c1")})
    assert home.load_lock()["ai"] == LockEntry("u", "c2", "c1")


def test_secret_is_stable_and_private(home):
    s = home.secret()
    assert s == home.secret() and len(s) >= 32
    assert oct(home.secret_path.stat().st_mode)[-3:] == "600"


def test_home_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("NGUI_HOME", str(tmp_path))
    assert home_from_env().root == tmp_path
