import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from ngui import gitops
from ngui.config import CORE_KEY, Config, Home, LockEntry
from ngui.loader import discover, plan
from ngui.manifest import ManifestError, load_manifest

log = logging.getLogger("ngui.manager")


class ManagerError(Exception):
    def __init__(self, key: str, **vars):
        super().__init__(key)
        self.key, self.vars = key, vars


@dataclass
class PluginStatus:
    id: str
    source: str  # "core" | "repo" | "link"
    enabled: bool
    role: str
    commit: str
    problem: str


def _clone(url: str, dest: Path) -> str:
    try:
        return gitops.clone(url, dest)
    except gitops.GitError as e:
        raise ManagerError("err.git", detail=str(e)) from e


class Manager:
    def __init__(self, home: Home):
        self.home = home

    def bootstrap(self) -> None:
        if not self.home.config_path.exists():
            self.home.save_config(Config(core_repo=os.environ.get("NGUI_CORE_REPO", "")))
        cfg, dest = self.home.load_config(), self.home.repos_dir / CORE_KEY
        if cfg.core_repo and not dest.exists():
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
        commit = _clone(url, dest)
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

    def remove(self, pid: str) -> None:
        cfg = self.home.load_config()
        if (self.home.repos_dir / CORE_KEY / pid).is_dir():
            raise ManagerError("err.is_core", id=pid)
        if pid in cfg.roles.values():
            raise ManagerError("err.fills_role", id=pid)
        dest = self.home.repos_dir / pid
        if not dest.is_dir():
            raise ManagerError("err.not_installed", id=pid)
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
        cfg.links[pid] = path
        if pid not in cfg.enabled:
            cfg.enabled.append(pid)
        self.home.save_config(cfg)

    def unlink(self, pid: str) -> None:
        cfg = self.home.load_config()
        cfg.links.pop(pid, None)
        self.home.save_config(cfg)

    def status(self) -> list[PluginStatus]:
        cfg, lock = self.home.load_config(), self.home.load_lock()
        found, manifests, problems = discover(self.home, cfg), {}, {}
        for pid, path in found.items():
            try:
                manifests[pid] = load_manifest(path, expected_id=pid)
            except ManifestError as e:
                problems[pid] = f"invalid manifest: {e}"
        _, broken = plan(manifests, cfg)
        problems = {**broken, **problems}
        rows = []
        for pid in sorted(set(found) | set(cfg.enabled) | set(cfg.roles.values())):
            m = manifests.get(pid)
            source = ("link" if pid in cfg.links else
                      "core" if (self.home.repos_dir / CORE_KEY / pid).is_dir() else "repo")
            role = m.provides if m and cfg.roles.get(m.provides) == pid else ""
            rows.append(PluginStatus(pid, source, pid in cfg.enabled or bool(role), role,
                                     lock[pid].commit if pid in lock else "", problems.get(pid, "")))
        return rows
