import pytest

from ngui import gitops
from ngui.manager import ManagerError

from ngui import KERNEL_DIR
from ngui.gitops import head
from ngui.loader import load
from ngui.manifest import ManifestError, load_manifest, localized
from ngui.scaffold import new_plugin


def test_scaffold_creates_loadable_plugin(tmp_path, kernel):
    path = new_plugin("notes", tmp_path)
    m = load_manifest(path, expected_id="notes")
    assert localized(m.name, "tr") and localized(m.name, "en")
    kernel.config.links["notes"] = str(path)
    kernel.config.enabled.append("notes")
    assert "notes" in load(kernel).loaded


def test_scaffold_is_git_repo(tmp_path):
    assert head(new_plugin("notes", tmp_path))


def test_scaffold_rejects_bad_name(tmp_path):
    with pytest.raises(ManifestError):
        new_plugin("Bad Name", tmp_path)


def test_scaffold_rejects_existing_target(tmp_path):
    new_plugin("notes", tmp_path)
    with pytest.raises(FileExistsError):
        new_plugin("notes", tmp_path)


def test_contract_mentions_every_role_method():
    text = (KERNEL_DIR / "CONTRACT.md").read_text()
    for name in ["for_plugin", "purge", "for_user", "shared", "current_user", "has", "set_mode",
                 "card", "kpi", "page_header", "page", "add", "ctx.t", "ctx.services", "ctx.bus"]:
        assert name in text, name


def test_scaffold_works_without_git_identity(tmp_path, monkeypatch):
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.delenv(f"GIT_{who}_NAME")
        monkeypatch.delenv(f"GIT_{who}_EMAIL")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert head(new_plugin("notes", tmp_path / "out"))


def test_scaffold_git_failure_cleans_up(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise gitops.GitError("no git")
    monkeypatch.setattr("ngui.scaffold.git", boom)
    with pytest.raises(ManagerError) as e:
        new_plugin("notes", tmp_path)
    assert e.value.key == "err.git"
    assert not (tmp_path / "nicegui-plugin-notes").exists()
