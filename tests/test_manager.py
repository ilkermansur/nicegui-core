import shutil

import pytest
from conftest import FIXTURES, commit_change

from ngui import gitops
from ngui.manager import ManagerError


def test_bootstrap_clones_core(mgr, core_url, monkeypatch):
    monkeypatch.setenv("NGUI_CORE_REPO", core_url); mgr.bootstrap()
    assert (mgr.home.repos_dir / "core-plugins" / "layout-fake" / "plugin.toml").exists()
    assert mgr.home.load_lock()["core-plugins"].url == core_url


def test_bootstrap_with_unreachable_core_does_not_raise(mgr, monkeypatch, tmp_path):
    monkeypatch.setenv("NGUI_CORE_REPO", str(tmp_path / "nope")); mgr.bootstrap()
    assert not (mgr.home.repos_dir / "core-plugins").exists()


def test_add_by_url(mgr, hello_url):
    assert mgr.add(hello_url) == "hello"
    assert "hello" in mgr.home.load_config().enabled and mgr.home.load_lock()["hello"].commit


def test_resolve_by_name_tries_sources_in_order(mgr, monkeypatch):
    cfg = mgr.home.load_config(); cfg.sources = ["example.com/a", "github.com/me"]; mgr.home.save_config(cfg)
    monkeypatch.setattr("ngui.manager.gitops.exists", lambda u: u == "https://github.com/me/nicegui-plugin-hello")
    assert mgr.resolve("hello") == ("hello", "https://github.com/me/nicegui-plugin-hello")


def test_resolve_unknown_name(mgr, monkeypatch):
    monkeypatch.setattr("ngui.manager.gitops.exists", lambda u: False)
    with pytest.raises(ManagerError) as e: mgr.resolve("nope")
    assert e.value.key == "err.not_found"


def test_add_failure_changes_nothing(mgr, tmp_path):
    before = (mgr.home.load_config(), mgr.home.load_lock())
    with pytest.raises(ManagerError) as e: mgr.add(str(tmp_path / "nicegui-plugin-nope"))
    assert e.value.key == "err.git"
    assert (mgr.home.load_config(), mgr.home.load_lock()) == before
    assert not (mgr.home.repos_dir / "nope").exists()


def test_add_bad_manifest_leaves_no_clone(mgr, make_repo, tmp_path):
    src = tmp_path / "src"; src.mkdir(); (src / "plugin.toml").write_text('id = "other"\nversion = "1"\n')
    url = make_repo(src, "nicegui-plugin-mismatch")
    from ngui.manifest import ManifestError
    with pytest.raises(ManifestError): mgr.add(url)
    assert not (mgr.home.repos_dir / "mismatch").exists()
    assert mgr.home.load_lock() == {}


def test_add_twice(mgr, hello_url):
    mgr.add(hello_url)
    with pytest.raises(ManagerError) as e: mgr.add(hello_url)
    assert e.value.key == "err.already_installed"


def test_add_refuses_core_plugin_id(mgr_with_core, tmp_path):
    with pytest.raises(ManagerError) as e: mgr_with_core.add(str(tmp_path / "nicegui-plugin-layout-fake"))
    assert e.value.key == "err.is_core"
    assert not (mgr_with_core.home.repos_dir / "layout-fake").exists()


def test_remove(mgr, hello_url):
    mgr.add(hello_url); mgr.remove("hello")
    assert not (mgr.home.repos_dir / "hello").exists() and "hello" not in mgr.home.load_config().enabled
    assert "hello" not in mgr.home.load_lock()


@pytest.mark.parametrize("pid,key", [("layout-fake", "err.is_core"), ("core", "err.is_core"), ("core-plugins", "err.is_core"),
                                     ("ghost", "err.not_installed")])
def test_remove_refusals(mgr_with_core, pid, key):
    with pytest.raises(ManagerError) as e: mgr_with_core.remove(pid)
    assert e.value.key == key


def test_disable_role_plugin_refused(mgr_with_core):
    with pytest.raises(ManagerError) as e: mgr_with_core.disable("layout-fake")
    assert e.value.key == "err.fills_role"


def test_enable_disable(mgr, hello_url):
    mgr.add(hello_url); mgr.disable("hello")
    assert "hello" not in mgr.home.load_config().enabled
    mgr.enable("hello"); assert "hello" in mgr.home.load_config().enabled
    with pytest.raises(ManagerError) as e: mgr.enable("ghost")
    assert e.value.key == "err.not_installed"


def test_use_checks_provides(mgr_with_core):
    with pytest.raises(ManagerError) as e: mgr_with_core.use("layout", "theme-fake")
    assert e.value.key == "err.wrong_role"
    mgr_with_core.use("theme", "theme-fake")
    assert mgr_with_core.home.load_config().roles["theme"] == "theme-fake"


def test_link_and_unlink(mgr, tmp_path):
    dev = shutil.copytree(FIXTURES / "plugins" / "hello", tmp_path / "dev")
    mgr.link("hello", str(dev)); assert mgr.home.load_config().links["hello"] == str(dev.resolve())
    mgr.unlink("hello"); assert "hello" not in mgr.home.load_config().links


def test_link_stores_absolute_path(mgr, tmp_path, monkeypatch):
    shutil.copytree(FIXTURES / "plugins" / "hello", tmp_path / "dev")
    monkeypatch.chdir(tmp_path)
    mgr.link("hello", "dev")
    assert mgr.home.load_config().links["hello"] == str((tmp_path / "dev").resolve())


def test_link_bad_path(mgr, tmp_path):
    with pytest.raises(ManagerError) as e: mgr.link("hello", str(tmp_path))
    assert e.value.key == "err.bad_path"


def test_status_reports_problems(mgr_with_core):
    cfg = mgr_with_core.home.load_config(); cfg.enabled.append("ghost"); mgr_with_core.home.save_config(cfg)
    st = {s.id: s for s in mgr_with_core.status()}
    assert st["ghost"].problem == "not installed" and st["layout-fake"].role == "layout" and st["layout-fake"].source == "core"


def test_status_and_sync_deps_honour_core_compat(mgr_with_core):
    from conftest import link_hello_with_deps
    calls = []; mgr_with_core.run_cmd = lambda cmd: calls.append(cmd)
    link_hello_with_deps(mgr_with_core, ["tinyhelper==1.0"])
    toml = mgr_with_core.home.root.parent / "hello-linked" / "plugin.toml"
    toml.write_text(toml.read_text() + 'core = ">=2"\n')
    assert {s.id: s for s in mgr_with_core.status()}["hello"].problem == "incompatible core: >=2"
    assert mgr_with_core.sync_deps() is False and calls == []


def test_bootstrap_adopts_env_core_repo_for_existing_config(mgr, core_url, monkeypatch):
    mgr.home.save_config(mgr.home.load_config())  # config exists, core_repo empty
    monkeypatch.setenv("NGUI_CORE_REPO", core_url); mgr.bootstrap()
    assert mgr.home.load_config().core_repo == core_url
    assert (mgr.home.repos_dir / "core-plugins" / "layout-fake").is_dir()


def test_bootstrap_reclones_half_cloned_core(mgr, core_url, monkeypatch):
    (mgr.home.repos_dir / "core-plugins" / "junk").mkdir(parents=True)
    monkeypatch.setenv("NGUI_CORE_REPO", core_url); mgr.bootstrap()
    assert (mgr.home.repos_dir / "core-plugins" / "layout-fake").is_dir()
    assert not (mgr.home.repos_dir / "core-plugins" / "junk").exists()


def test_remove_core_plugins_keeps_core_repo(mgr_with_core):
    with pytest.raises(ManagerError): mgr_with_core.remove("core-plugins")
    assert (mgr_with_core.home.repos_dir / "core-plugins" / "layout-fake").is_dir()


def test_bootstrap_reclone_returns_to_locked_commit(mgr, core_url, monkeypatch):
    monkeypatch.setenv("NGUI_CORE_REPO", core_url); mgr.bootstrap()
    pinned = mgr.home.load_lock()["core-plugins"].commit
    commit_change(core_url)  # upstream moves on
    (mgr.home.repos_dir / "core-plugins" / ".git" / "HEAD").unlink()  # half-broken clone
    mgr.bootstrap()
    assert gitops.head(mgr.home.repos_dir / "core-plugins") == pinned
    assert mgr.home.load_lock()["core-plugins"].commit == pinned


def test_bootstrap_reclone_with_vanished_commit_takes_head(mgr, core_url, monkeypatch):
    monkeypatch.setenv("NGUI_CORE_REPO", core_url); mgr.bootstrap()
    lock = mgr.home.load_lock(); lock["core-plugins"].commit = "0" * 40; mgr.home.save_lock(lock)
    shutil.rmtree(mgr.home.repos_dir / "core-plugins")
    mgr.bootstrap()
    head = gitops.head(mgr.home.repos_dir / "core-plugins")
    assert mgr.home.load_lock()["core-plugins"].commit == head
