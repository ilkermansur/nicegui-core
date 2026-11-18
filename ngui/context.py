import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ngui.bus import Bus, Services
from ngui.config import Config, Home
from ngui.i18n import I18n
from ngui.manifest import Manifest


@dataclass
class Kernel:
    home: Home
    config: Config
    bus: Bus
    services: Services
    i18n: I18n
    roles: dict[str, Any] = field(default_factory=dict)
    manager: Any = None
    result: Any = None
    restart: Callable[[], None] = lambda: None


class Context:
    def __init__(self, manifest: Manifest, kernel: Kernel):
        self.manifest = manifest
        self.kernel = kernel
        self.id = manifest.id
        self.path = manifest.path
        self.log = logging.getLogger(f"ngui.{manifest.id}")
        self.bus = kernel.bus
        self.services = kernel.services
        self.i18n = kernel.i18n

    def role(self, name: str) -> Any:
        try:
            return self.kernel.roles[name]
        except KeyError:
            raise LookupError(f"role '{name}' is not loaded") from None

    @property
    def storage(self):
        return self.role("storage").for_plugin(self.id)

    def t(self, key: str, **vars) -> str:
        return self.i18n.t(self.id, key, **vars)
