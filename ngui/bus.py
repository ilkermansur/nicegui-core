import inspect
import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)


class Bus:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable]] = {}

    def on(self, event: str, fn: Callable) -> None:
        self._listeners.setdefault(event, []).append(fn)

    def off(self, event: str, fn: Callable) -> None:
        if fn in self._listeners.get(event, []):
            self._listeners[event].remove(fn)

    def emit(self, event: str, data: Any = None) -> None:
        for fn in list(self._listeners.get(event, [])):
            try:
                result = fn(data)
                if inspect.isawaitable(result):
                    self._schedule(event, result)
            except Exception:
                log.exception("bus: listener for %r failed", event)

    @staticmethod
    def _schedule(event: str, awaitable: Any) -> None:
        try:
            from nicegui import background_tasks
            background_tasks.create(awaitable, name=f"bus:{event}")
        except Exception:
            if inspect.iscoroutine(awaitable):
                awaitable.close()
            log.exception("bus: could not schedule async listener for %r", event)


class Services:
    def __init__(self) -> None:
        self._items: dict[str, Any] = {}

    def provide(self, name: str, obj: Any) -> None:
        if name in self._items:
            log.warning("services: %r provided again, overwriting", name)
        self._items[name] = obj

    def get(self, name: str) -> Any | None:
        return self._items.get(name)
