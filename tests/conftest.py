import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ngui.config import Home


@pytest.fixture
def home(tmp_path):
    return Home(tmp_path / "home")


@pytest.fixture(autouse=True)
def git_identity(monkeypatch):
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "test@example.com")


@pytest.fixture
def make_repo(tmp_path):
    def make(src: Path, name: str) -> str:
        dest = tmp_path / "remotes" / name
        shutil.copytree(src, dest)
        for cmd in (["init", "-b", "main"], ["add", "-A"], ["commit", "-m", "init"]):
            subprocess.run(["git", *cmd], cwd=dest, check=True, capture_output=True)
        return str(dest)

    return make


FIXTURES = Path(__file__).parent / "fixtures"
CORE_ROLES = {"storage": "storage-mem", "auth": "auth-fake",
              "theme": "theme-fake", "layout": "layout-fake"}


@pytest.fixture
def install_fixtures(home):
    def install(*names):
        for name in names:
            core = FIXTURES / "core-plugins" / name
            src, dest = (core, home.repos_dir / "core-plugins" / name) if core.is_dir() else (
                FIXTURES / "plugins" / name, home.repos_dir / name)
            shutil.copytree(src, dest)

    return install


@pytest.fixture
def kernel(home, install_fixtures):
    from ngui.bus import Bus, Services
    from ngui.config import Config
    from ngui.context import Kernel
    from ngui.i18n import I18n

    install_fixtures(*CORE_ROLES.values(), "hello", "boom", "needs-missing")
    cfg = Config(enabled=[], roles=dict(CORE_ROLES))
    return Kernel(home, cfg, Bus(), Services(), I18n("tr"))


def commit_change(url: str, relpath: str = "CHANGES", append: str = "x\n") -> str:
    path = Path(url) / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(append)
    for cmd in (["add", "-A"], ["commit", "-m", "change"]):
        subprocess.run(["git", *cmd], cwd=url, check=True, capture_output=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=url, check=True,
                          capture_output=True, text=True).stdout.strip()


def fake_roles(home: Home) -> None:
    cfg = home.load_config()
    cfg.roles, cfg.enabled = dict(CORE_ROLES), list(CORE_ROLES.values())
    home.save_config(cfg)


@pytest.fixture
def mgr(home):
    from ngui.manager import Manager

    return Manager(home)


@pytest.fixture
def core_url(make_repo):
    return make_repo(FIXTURES / "core-plugins", "core-plugins")


@pytest.fixture
def hello_url(make_repo):
    return make_repo(FIXTURES / "plugins" / "hello", "nicegui-plugin-hello")


@pytest.fixture
def mgr_with_core(mgr, core_url, monkeypatch):
    monkeypatch.setenv("NGUI_CORE_REPO", core_url)
    mgr.bootstrap()
    fake_roles(mgr.home)
    return mgr


def link_hello_with_deps(mgr, deps: list[str]) -> None:
    dest = mgr.home.root.parent / "hello-linked"
    shutil.copytree(FIXTURES / "plugins" / "hello", dest)
    with (dest / "plugin.toml").open("a") as f:
        f.write(f"\ndependencies = {json.dumps(deps)}\n")
    mgr.link("hello", str(dest))
