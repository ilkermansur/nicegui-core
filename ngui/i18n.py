import logging
import tomllib
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)


class I18n:
    def __init__(self, default_lang: str = "tr"):
        self.default_lang = default_lang
        self.lang_getter: Callable[[], str | None] | None = None
        self.lang_setter: Callable[[str], None] | None = None
        self._tables: dict[str, dict[str, dict[str, str]]] = {}  # ns -> lang -> key -> text

    def load(self, namespace: str, locales_dir: Path) -> None:
        if not locales_dir.is_dir():
            return
        for f in sorted(locales_dir.glob("*.toml")):
            try:
                data = tomllib.loads(f.read_text(encoding="utf-8"))
            except (tomllib.TOMLDecodeError, OSError) as e:
                log.warning("i18n: skipping %s: %s", f, e)
                continue
            self._tables.setdefault(namespace, {}).setdefault(f.stem, {}).update(data)

    def current_lang(self) -> str:
        try:
            if self.lang_getter and (lang := self.lang_getter()):
                return lang
        except Exception as e:  # e.g. storage outside a request: expected, not alarming
            log.debug("i18n: lang_getter failed: %r", e)
        return self.default_lang

    def t(self, namespace: str, key: str, lang: str | None = None, **vars) -> str:
        langs = self._tables.get(namespace, {})
        text = key
        for code in (lang or self.current_lang(), "en"):
            if key in langs.get(code, {}):
                text = langs[code][key]
                break
        if vars:
            try:
                return text.format(**vars)
            except (KeyError, IndexError, ValueError):
                return text
        return text

    def set_lang(self, lang: str) -> None:
        if self.lang_setter:
            self.lang_setter(lang)
        try:
            from nicegui import ui
            from nicegui.slot import Slot

            if Slot.get_stack():  # only inside a UI context
                ui.navigate.reload()
        except Exception:
            pass

    def languages(self) -> list[str]:
        return sorted({lang for langs in self._tables.values() for lang in langs})
