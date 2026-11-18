import os
import secrets
import tempfile
import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import tomli_w

from ngui import NguiError

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


def _known(cls, data: dict) -> dict:
    names = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in names}


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
        try:
            return tomllib.loads(path.read_text()) if path.exists() else {}
        except tomllib.TOMLDecodeError as e:
            raise NguiError("err.config", path=str(path), detail=str(e)) from e

    def _write(self, path: Path, data: dict) -> None:
        self._atomic_write(path, tomli_w.dumps(data))

    def _atomic_write(self, path: Path, text: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.root)  # mkstemp creates mode 0o600
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)

    def load_config(self) -> Config:
        return Config(**_known(Config, self._read(self.config_path)))

    def save_config(self, cfg: Config) -> None:
        self._write(self.config_path, asdict(cfg))

    def load_lock(self) -> dict[str, LockEntry]:
        return {k: LockEntry(**_known(LockEntry, v)) for k, v in self._read(self.lock_path).items()}

    def save_lock(self, lock: dict[str, LockEntry]) -> None:
        self._write(self.lock_path, {k: asdict(v) for k, v in lock.items()})

    def secret(self) -> str:
        if not self.secret_path.exists():
            self._atomic_write(self.secret_path, secrets.token_hex(32))  # mode 0o600
        return self.secret_path.read_text()


def home_from_env() -> Home:
    return Home(Path(os.environ.get("NGUI_HOME", "/data")))
