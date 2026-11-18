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
