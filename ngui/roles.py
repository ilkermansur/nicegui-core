from collections.abc import Callable
from typing import Protocol, TypedDict

ROLE_ORDER = ("storage", "auth", "theme", "layout")


class User(TypedDict):
    id: str
    name: str
    roles: list[str]


class PluginStore(Protocol):
    shared: "PluginStore"

    def get(self, key: str, default=None): ...
    def set(self, key: str, value) -> None: ...
    def delete(self, key: str) -> None: ...
    def list(self, prefix: str = "") -> list[str]: ...
    def for_user(self, user_id: str) -> "PluginStore": ...


class StorageRole(Protocol):
    def for_plugin(self, plugin_id: str) -> PluginStore: ...
    def purge(self, plugin_id: str) -> None: ...


class AuthRole(Protocol):
    def current_user(self) -> User: ...
    def has(self, permission: str) -> bool: ...


class ThemeRole(Protocol):
    mode: str

    def set_mode(self, mode: str) -> None: ...
    def card(self, title: str | None = None, actions: Callable | None = None, meta: str | None = None): ...
    def kpi(self, label: str, value, icon: str | None = None, tone: str = "neutral",
            delta: str | None = None, trend: str | None = None): ...
    def page_header(self, title: str, description: str | None = None, actions: Callable | None = None): ...


class LayoutRole(Protocol):
    def page(
        self,
        path: str,
        title: str | Callable[[], str],
        icon: str | None = None,
        permission: str | None = None,
    ) -> Callable: ...
    def add(self, slot: str, builder: Callable[[], None]) -> None: ...
