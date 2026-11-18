from subprocess import CompletedProcess

import pytest
from conftest import commit_change, link_hello_with_deps

from ngui.config import LockEntry
from ngui.gitops import head
from ngui.manager import ManagerError


def test_update_and_rollback(mgr, hello_url):
    mgr.add(hello_url); first = mgr.home.load_lock()["hello"].commit
    commit_change(hello_url); second = mgr.update("hello")
    assert second != first and mgr.home.load_lock()["hello"].previous == first
    assert mgr.rollback("hello") == first
    assert mgr.home.load_lock()["hello"] == LockEntry(hello_url, first, second)


def test_update_without_changes_keeps_previous(mgr, hello_url):
    mgr.add(hello_url); first = mgr.home.load_lock()["hello"].commit
    assert mgr.update("hello") == first
    assert mgr.home.load_lock()["hello"].previous == ""


def test_rollback_without_previous(mgr, hello_url):
    mgr.add(hello_url)
    with pytest.raises(ManagerError) as e: mgr.rollback("hello")
    assert e.value.key == "err.no_previous"


def test_core_update_refused_when_incompatible(mgr_with_core, core_url):
    old = mgr_with_core.home.load_lock()["core-plugins"].commit
    commit_change(core_url, "layout-fake/plugin.toml", append='\ncore = ">=2"')
    with pytest.raises(ManagerError) as e: mgr_with_core.update("core")
    assert e.value.key == "err.needs_self_update"
    assert head(mgr_with_core.home.repos_dir / "core-plugins") == old
    assert mgr_with_core.home.load_lock()["core-plugins"].commit == old


def test_sync_deps_installs_once(mgr_with_core, hello_url):
    calls = []; mgr_with_core.run_cmd = lambda cmd: calls.append(cmd) or CompletedProcess(cmd, 0, "", "")
    link_hello_with_deps(mgr_with_core, ["tinyhelper==1.0"])
    assert mgr_with_core.sync_deps() is True and calls[-1][-1] == "tinyhelper==1.0"
    assert mgr_with_core.sync_deps() is False and len(calls) == 1


def test_sync_deps_failure(mgr_with_core):
    mgr_with_core.run_cmd = lambda cmd: CompletedProcess(cmd, 1, "", "conflict")
    link_hello_with_deps(mgr_with_core, ["tinyhelper==1.0"])
    with pytest.raises(ManagerError) as e: mgr_with_core.sync_deps()
    assert e.value.key == "err.deps"


def test_catalog_lists_prefixed_repos(mgr, monkeypatch):
    cfg = mgr.home.load_config(); cfg.sources = ["github.com/me"]; mgr.home.save_config(cfg)
    monkeypatch.setattr("ngui.manager.fetch_json", lambda url: [
        {"name": "nicegui-plugin-ai", "description": "x", "html_url": "https://github.com/me/nicegui-plugin-ai"},
        {"name": "other-repo", "description": "", "html_url": "u"}])
    assert [c.id for c in mgr.catalog()] == ["ai"]


def test_catalog_survives_network_error(mgr, monkeypatch):
    cfg = mgr.home.load_config(); cfg.sources = ["github.com/me"]; mgr.home.save_config(cfg)
    monkeypatch.setattr("ngui.manager.fetch_json", lambda url: (_ for _ in ()).throw(OSError("offline")))
    assert mgr.catalog() == []


def test_self_update_without_git(mgr, tmp_path):
    with pytest.raises(ManagerError) as e: mgr.self_update(tmp_path)
    assert e.value.key == "err.self_update_docker"


def test_failed_update_restores_lock_commit(mgr, hello_url):
    import shutil
    mgr.add(hello_url); first = mgr.home.load_lock()["hello"].commit
    commit_change(hello_url); mgr.update("hello"); mgr.rollback("hello")
    shutil.rmtree(hello_url)
    with pytest.raises(ManagerError) as e: mgr.update("hello")
    assert e.value.key == "err.git"
    assert head(mgr.home.repos_dir / "hello") == first == mgr.home.load_lock()["hello"].commit


def test_rollback_without_repo_dir(mgr, hello_url):
    import shutil
    mgr.add(hello_url); commit_change(hello_url); mgr.update("hello")
    shutil.rmtree(mgr.home.repos_dir / "hello")
    with pytest.raises(ManagerError) as e: mgr.rollback("hello")
    assert e.value.key == "err.not_installed"


@pytest.mark.parametrize("op", ["update", "rollback", "remove"])
def test_core_plugin_id_is_refused(mgr_with_core, op):
    with pytest.raises(ManagerError) as e: getattr(mgr_with_core, op)("layout-fake")
    assert e.value.key == "err.is_core"


def test_fetch_json_token_not_sent_on_redirect(monkeypatch):
    import io
    from ngui.manager import fetch_json
    seen = []
    monkeypatch.setenv("GITHUB_TOKEN", "t0k")
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: seen.append(req) or io.BytesIO(b"[]"))
    assert fetch_json("https://api.github.com/x") == []
    assert seen[0].unredirected_hdrs["Authorization"] == "Bearer t0k" and "Authorization" not in seen[0].headers
