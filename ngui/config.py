import os
import secrets
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path

import tomli_w

CORE_KEY = "core-plugins"
DEFAULT_ROLES = {"storage": "storage-sqlite", "auth": "auth-local",
                 "theme": "theme-default", "layout": "layout-sidebar"}
DEFAULT_ENABLED = ["storage-sqlite", "auth-local", "theme-default", "layout-sidebar", "store"]


@dataclass
class Config:
    default_lang: str = "tr"
    core_repo: str = ""
    sources: list[str] = field(default_factory=list)
    enabled: list[str] = field(default_factory=lambda: list(DEFAULT_ENABLED))
    roles: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ROLES))
    links: dict[str, str] = field(default_factory=dict)


@dataclass
class LockEntry:
    url: str
    commit: str
    previous: str = ""


class Home:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.repos_dir = self.root / "repos"
        self.pydeps_dir = self.root / "pydeps"
        self.data_dir = self.root / "data"
        self.config_path = self.root / "config.toml"
        self.lock_path = self.root / "plugins.lock"
        self.pid_path = self.root / "ngui.pid"
        self.secret_path = self.root / "secret"

    def _read(self, path: Path) -> dict:
        return tomllib.loads(path.read_text()) if path.exists() else {}

    def _write(self, path: Path, data: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path.write_text(tomli_w.dumps(data))

    def load_config(self) -> Config:
        return Config(**self._read(self.config_path))

    def save_config(self, cfg: Config) -> None:
        self._write(self.config_path, asdict(cfg))

    def load_lock(self) -> dict[str, LockEntry]:
        return {k: LockEntry(**v) for k, v in self._read(self.lock_path).items()}

    def save_lock(self, lock: dict[str, LockEntry]) -> None:
        self._write(self.lock_path, {k: asdict(v) for k, v in lock.items()})

    def secret(self) -> str:
        if not self.secret_path.exists():
            self.root.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(secrets.token_hex(32))
        return self.secret_path.read_text()


def home_from_env() -> Home:
    return Home(Path(os.environ.get("NGUI_HOME", "/data")))
