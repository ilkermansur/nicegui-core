import pytest

from ngui.gitops import GitError, _env, checkout, clone, exists, head, pull
from conftest import FIXTURES, commit_change


def test_clone_and_head(make_repo, tmp_path):
    url = make_repo(FIXTURES / "plugins" / "hello", "nicegui-plugin-hello")
    c = clone(url, tmp_path / "w")
    assert c == head(tmp_path / "w") and len(c) == 40


def test_clone_failure_leaves_nothing(tmp_path):
    with pytest.raises(GitError):
        clone(str(tmp_path / "nope"), tmp_path / "w")
    assert not (tmp_path / "w").exists()


def test_pull_then_checkout_back(make_repo, tmp_path):
    url = make_repo(FIXTURES / "plugins" / "hello", "r")
    first = clone(url, tmp_path / "w")
    commit_change(url)
    second = pull(tmp_path / "w")
    assert second != first
    checkout(tmp_path / "w", first)
    assert head(tmp_path / "w") == first
    assert pull(tmp_path / "w") == second


def test_exists(make_repo, tmp_path):
    assert exists(make_repo(FIXTURES / "plugins" / "hello", "r"))
    assert not exists(str(tmp_path / "nope"))


def test_token_goes_through_env_only(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t0k")
    env = _env()
    assert env["GIT_CONFIG_KEY_0"] == "http.https://github.com/.extraheader"
    assert "t0k" not in env["GIT_CONFIG_VALUE_0"]
