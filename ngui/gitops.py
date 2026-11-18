"""Thin wrappers around the git CLI. The token only ever travels via env vars."""
import base64
import os
import shutil
import subprocess
from pathlib import Path


class GitError(Exception):
    pass


def _env() -> dict[str, str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    if token := os.environ.get("GITHUB_TOKEN"):
        creds = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env.update(GIT_CONFIG_COUNT="1",
                   GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
                   GIT_CONFIG_VALUE_0=f"AUTHORIZATION: basic {creds}")
    return env


def _git(*args: str, cwd: Path | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=_env())
    if r.returncode:
        raise GitError(r.stderr.strip())
    return r.stdout.strip()


def head(dest: Path) -> str:
    return _git("rev-parse", "HEAD", cwd=dest)


def clone(url: str, dest: Path) -> str:
    try:
        _git("clone", url, str(dest))
        return head(dest)
    except GitError:
        shutil.rmtree(dest, ignore_errors=True)
        raise


def pull(dest: Path) -> str:
    branch = _git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=dest).removeprefix("origin/")
    _git("checkout", branch, cwd=dest)
    _git("pull", "--ff-only", cwd=dest)
    return head(dest)


def checkout(dest: Path, commit: str) -> None:
    _git("checkout", "--detach", commit, cwd=dest)


def exists(url: str) -> bool:
    r = subprocess.run(["git", "ls-remote", "--exit-code", url], capture_output=True, env=_env())
    return r.returncode == 0
