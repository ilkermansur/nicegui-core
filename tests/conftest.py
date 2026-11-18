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
