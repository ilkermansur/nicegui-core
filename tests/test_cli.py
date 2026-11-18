import re
import tomllib

from ngui import KERNEL_DIR
from ngui.cli import main


def test_add_list_remove(home_env, hello_url, capsys):
    assert main(["add", hello_url]) == 0
    assert main(["list"]) == 0 and "hello" in capsys.readouterr().out
    assert main(["remove", "hello"]) == 0


def test_error_is_translated_tr(home_env, capsys, monkeypatch):
    monkeypatch.setenv("NGUI_LANG", "tr")
    assert main(["remove", "ghost"]) == 1
    assert "kurulu değil" in capsys.readouterr().err


def test_error_is_translated_en(home_env, capsys, monkeypatch):
    monkeypatch.setenv("NGUI_LANG", "en")
    assert main(["remove", "ghost"]) == 1
    assert "Not installed" in capsys.readouterr().err


def test_manifest_error_returns_1(home_env, tmp_path, capsys):
    bad = tmp_path / "nicegui-plugin-bad"
    bad.mkdir()
    (bad / "plugin.toml").write_text("id = ")
    assert main(["add", str(bad)]) == 1


def test_change_signals_running_app(home_env, hello_url, monkeypatch):
    seen = []
    monkeypatch.setattr("ngui.cli.signal_app", lambda h: seen.append(h) or False)
    main(["add", hello_url])
    assert len(seen) == 1


def test_not_running_message(home_env, hello_url, capsys, monkeypatch):
    monkeypatch.setenv("NGUI_LANG", "en")
    monkeypatch.setattr("ngui.cli.signal_app", lambda h: False)
    main(["add", hello_url])
    assert "not running" in capsys.readouterr().out


def test_run_calls_app_run(monkeypatch):
    called = []
    monkeypatch.setattr("ngui.cli.run", lambda: called.append(1))
    assert main(["run"]) == 0 and called == [1]


def test_new_creates_scaffold(home_env, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("NGUI_LANG", "en")
    assert main(["new", "x", "--dir", str(tmp_path)]) == 0
    assert (tmp_path / "nicegui-plugin-x" / "plugin.toml").is_file()
    assert "scaffold created" in capsys.readouterr().out
    assert main(["new", "x", "--dir", str(tmp_path)]) == 1
    assert "Already exists" in capsys.readouterr().err
    assert main(["new", "Bad Name", "--dir", str(tmp_path)]) == 1


def test_every_locale_key_has_tr_and_en():
    keys = {k for f in (KERNEL_DIR / "ngui").glob("*.py")
            for k in re.findall(r'"((?:err|cli|recovery)\.[a-z_]+)"', f.read_text())}
    assert "err.git" in keys and "recovery.title" in keys
    for lang in ("tr", "en"):
        table = tomllib.loads((KERNEL_DIR / "ngui" / "locales" / f"{lang}.toml").read_text())
        assert keys <= set(table), (lang, keys - set(table))


def test_every_mutating_command_syncs_deps(home_env, hello_url, monkeypatch):
    synced = []
    monkeypatch.setattr("ngui.cli.Manager.sync_deps", lambda self: synced.append(1))
    main(["add", hello_url]); main(["disable", "hello"]); main(["remove", "hello"])
    assert synced == [1, 1, 1]


def test_broken_config_is_reported(home_env, capsys, monkeypatch):
    monkeypatch.setenv("NGUI_LANG", "en")
    home_env.config_path.write_text("enabled = [")
    assert main(["list"]) == 1
    err = capsys.readouterr().err
    assert "Invalid config file" in err and str(home_env.config_path) in err
