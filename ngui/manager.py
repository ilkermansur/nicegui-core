import json
import logging
import os
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ngui import NguiError, gitops
from ngui.config import CORE_KEY, Config, Home, LockEntry
from ngui.loader import discover, plan, read_manifests
from ngui.manifest import ManifestError, core_compatible, load_manifest

log = logging.getLogger("ngui.manager")


ManagerError = NguiError


@dataclass
class PluginStatus:
    id: str
    source: str  # "core" | "repo" | "link"
    enabled: bool
    role: str
    commit: str
    problem: str


@dataclass
class CatalogEntry:
    id: str
    description: str
    url: str


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


class Manager:
    def __init__(self, home: Home):
        self.home = home
        self.run_cmd: Callable[[list[str]], subprocess.CompletedProcess] = _run

    def bootstrap(self) -> None:
        cfg, dest = self.home.load_config(), self.home.repos_dir / CORE_KEY
        if not cfg.core_repo:  # first boot, or NGUI_CORE_REPO set later
            cfg.core_repo = os.environ.get("NGUI_CORE_REPO", "")
            self.home.save_config(cfg)
        if cfg.core_repo and not (dest / ".git" / "HEAD").is_file():
            shutil.rmtree(dest, ignore_errors=True)  # missing or a half-finished clone
            try:
                commit = gitops.clone(cfg.core_repo, dest)
            except gitops.GitError as e:
                log.error("core plugins clone failed: %s", e)
                return
            lock = self.home.load_lock()
            lock[CORE_KEY] = LockEntry(cfg.core_repo, commit)
            self.home.save_lock(lock)

    def resolve(self, name_or_url: str) -> tuple[str, str]:
        if "://" in name_or_url or "/" in name_or_url or os.path.exists(name_or_url):
            pid = Path(name_or_url.rstrip("/")).name.removesuffix(".git").removeprefix("nicegui-plugin-")
            return pid, name_or_url
        for source in self.home.load_config().sources:
            url = f"https://{source}/nicegui-plugin-{name_or_url}"
            if gitops.exists(url):
                return name_or_url, url
        raise ManagerError("err.not_found", name=name_or_url)

    def add(self, name_or_url: str) -> str:
        pid, url = self.resolve(name_or_url)
        dest = self.home.repos_dir / pid
        if dest.exists():
            raise ManagerError("err.already_installed", id=pid)
        commit = gitops.clone(url, dest)
        try:
            load_manifest(dest, expected_id=pid)
        except ManifestError:
            shutil.rmtree(dest, ignore_errors=True)
            raise
        lock, cfg = self.home.load_lock(), self.home.load_config()
        lock[pid] = LockEntry(url, commit)
        if pid not in cfg.enabled:
            cfg.enabled.append(pid)
        self.home.save_lock(lock)
        self.home.save_config(cfg)
        return pid

    def _require_installed(self, pid: str, cfg: Config) -> None:
        if pid not in discover(self.home, cfg):
            raise ManagerError("err.not_installed", id=pid)

    def _repo(self, pid: str) -> tuple[str, Path]:
        """Lock key and clone dir of an installed repo; `core` is the core-plugins repo."""
        if (self.home.repos_dir / CORE_KEY / pid).is_dir():
            raise ManagerError("err.is_core", id=pid)
        key = CORE_KEY if pid == "core" else pid
        if not (self.home.repos_dir / key).is_dir():
            raise ManagerError("err.not_installed", id=pid)
        return key, self.home.repos_dir / key

    def remove(self, pid: str) -> None:
        cfg = self.home.load_config()
        if pid == "core":
            raise ManagerError("err.is_core", id=pid)
        _, dest = self._repo(pid)
        if pid in cfg.roles.values():
            raise ManagerError("err.fills_role", id=pid)
        shutil.rmtree(dest)
        lock = self.home.load_lock()
        lock.pop(pid, None)
        self.home.save_lock(lock)
        cfg.enabled = [p for p in cfg.enabled if p != pid]
        cfg.links.pop(pid, None)
        self.home.save_config(cfg)

    def enable(self, pid: str) -> None:
        cfg = self.home.load_config()
        self._require_installed(pid, cfg)
        if pid not in cfg.enabled:
            cfg.enabled.append(pid)
            self.home.save_config(cfg)

    def disable(self, pid: str) -> None:
        cfg = self.home.load_config()
        self._require_installed(pid, cfg)
        if pid in cfg.roles.values():
            raise ManagerError("err.fills_role", id=pid)
        cfg.enabled = [p for p in cfg.enabled if p != pid]
        self.home.save_config(cfg)

    def use(self, role: str, pid: str) -> None:
        cfg = self.home.load_config()
        self._require_installed(pid, cfg)
        if load_manifest(discover(self.home, cfg)[pid], expected_id=pid).provides != role:
            raise ManagerError("err.wrong_role", id=pid, role=role)
        cfg.roles[role] = pid
        self.home.save_config(cfg)

    def link(self, pid: str, path: str) -> None:
        if not (Path(path).expanduser() / "plugin.toml").is_file():
            raise ManagerError("err.bad_path", path=path)
        cfg = self.home.load_config()
        cfg.links[pid] = str(Path(path).expanduser().resolve())
        if pid not in cfg.enabled:
            cfg.enabled.append(pid)
        self.home.save_config(cfg)

    def unlink(self, pid: str) -> None:
        cfg = self.home.load_config()
        cfg.links.pop(pid, None)
        self.home.save_config(cfg)

    def status(self) -> list[PluginStatus]:
        cfg, lock = self.home.load_config(), self.home.load_lock()
        found, (manifests, bad) = discover(self.home, cfg), read_manifests(self.home, cfg)
        problems = {**plan(manifests, cfg)[1], **bad}
        rows = []
        for pid in sorted(set(found) | set(cfg.enabled) | set(cfg.roles.values())):
            m = manifests.get(pid)
            source = ("link" if pid in cfg.links else
                      "core" if (self.home.repos_dir / CORE_KEY / pid).is_dir() else "repo")
            role = m.provides if m and cfg.roles.get(m.provides) == pid else ""
            rows.append(PluginStatus(pid, source, pid in cfg.enabled or bool(role), role,
                                     lock[pid].commit if pid in lock else "", problems.get(pid, "")))
        return rows

    def update(self, pid: str) -> str:
        key, dest = self._repo(pid)
        lock = self.home.load_lock()
        if key not in lock:
            raise ManagerError("err.not_installed", id=pid)
        old = lock[key].commit
        try:
            if (new := gitops.pull(dest)) == old:
                return new
            for toml in [dest / "plugin.toml", *dest.glob("*/plugin.toml")]:
                m = load_manifest(toml.parent) if toml.is_file() else None
                if m and not core_compatible(m.core):
                    raise ManagerError("err.needs_self_update", plugin=m.id, spec=m.core)
        except Exception as e:
            gitops.checkout(dest, old)
            if isinstance(e, ManifestError):
                raise ManagerError("err.manifest", detail=str(e)) from e
            raise
        lock[key] = LockEntry(lock[key].url, new, previous=old)
        self.home.save_lock(lock)
        return new

    def rollback(self, pid: str) -> str:
        key, dest = self._repo(pid)
        lock = self.home.load_lock()
        if key not in lock:
            raise ManagerError("err.not_installed", id=pid)
        entry = lock[key]
        if not entry.previous:
            raise ManagerError("err.no_previous")
        gitops.checkout(dest, entry.previous)
        lock[key] = LockEntry(entry.url, entry.previous, entry.commit)
        self.home.save_lock(lock)
        return entry.previous

    def sync_deps(self) -> bool:
        cfg = self.home.load_config()
        manifests = read_manifests(self.home, cfg)[0]
        order, _ = plan(manifests, cfg)
        specs = sorted({d for pid in order for d in manifests[pid].dependencies})
        marker = self.home.pydeps_dir / ".installed.json"
        try:
            if json.loads(marker.read_text()) == specs:
                return False
        except (OSError, ValueError):
            pass
        if not specs:
            return False
        self.home.pydeps_dir.mkdir(parents=True, exist_ok=True)
        base = ["uv", "pip"] if shutil.which("uv") else [sys.executable, "-m", "pip"]
        r = self.run_cmd([*base, "install", "--target", str(self.home.pydeps_dir), *specs])
        if r.returncode:
            raise ManagerError("err.deps", detail=r.stderr)
        marker.write_text(json.dumps(specs))
        return True

    def self_update(self, kernel_dir: Path) -> str:
        if not (Path(kernel_dir) / ".git").exists():
            raise ManagerError("err.self_update_docker")
        return gitops.pull(Path(kernel_dir))

    def catalog(self) -> list[CatalogEntry]:
        entries = []
        for source in self.home.load_config().sources:
            host, _, owner = source.partition("/")
            if host != "github.com" or not owner:
                continue
            try:
                repos = fetch_json(f"https://api.github.com/users/{owner}/repos?per_page=100")
                entries += [CatalogEntry(r["name"].removeprefix("nicegui-plugin-"),
                                         r.get("description") or "", r["html_url"])
                            for r in repos if r["name"].startswith("nicegui-plugin-")]
            except (OSError, ValueError, KeyError, TypeError) as e:
                log.warning("catalog fetch failed for %s: %s", source, e)
        return entries
