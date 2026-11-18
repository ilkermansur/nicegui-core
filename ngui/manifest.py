import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet

from ngui import CONTRACT_VERSION, NguiError
from ngui.roles import ROLE_ORDER

ID_PATTERN = re.compile(r"[a-z][a-z0-9-]*")
RESERVED_IDS = {"core", "core-plugins"}


class ManifestError(NguiError):
    def __init__(self, detail: str):
        super().__init__("err.manifest", detail=detail)


@dataclass
class Manifest:
    id: str
    name: dict[str, str]
    version: str
    description: dict[str, str]
    core: str
    provides: str
    requires: list[str]
    dependencies: list[str]
    permissions: list[str]
    path: Path


def _text(data: dict, key: str) -> dict[str, str]:
    value = data.get(key, {})
    if isinstance(value, str):
        return {"en": value}
    if isinstance(value, dict) and all(isinstance(v, str) for v in value.values()):
        return dict(value)
    raise ManifestError(f"'{key}' must be a string or a table of strings")


def _list(data: dict, key: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ManifestError(f"'{key}' must be a list of strings")
    return list(value)


def load_manifest(path: Path, expected_id: str | None = None) -> Manifest:
    file = Path(path) / "plugin.toml"
    try:
        data = tomllib.loads(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as e:
        raise ManifestError(f"cannot read {file}: {e}") from e
    except tomllib.TOMLDecodeError as e:
        raise ManifestError(f"invalid TOML in {file}: {e}") from e
    plugin_id, version = data.get("id"), data.get("version")
    if not isinstance(plugin_id, str) or not isinstance(version, str) or not version:
        raise ManifestError(f"{file}: 'id' and 'version' are required strings")
    if not ID_PATTERN.fullmatch(plugin_id) or plugin_id in RESERVED_IDS:
        raise ManifestError(f"{file}: invalid or reserved id '{plugin_id}'")
    if expected_id is not None and plugin_id != expected_id:
        raise ManifestError(f"{file}: id '{plugin_id}' does not match '{expected_id}'")
    provides = data.get("provides", "")
    if not isinstance(provides, str):
        raise ManifestError(f"{file}: 'provides' must be a string")
    if provides and provides not in ROLE_ORDER:
        raise ManifestError(f"{file}: unknown role '{provides}'")
    core = data.get("core", ">=1,<2")
    if not isinstance(core, str):
        raise ManifestError(f"{file}: 'core' must be a string")
    return Manifest(
        id=plugin_id,
        name=_text(data, "name"),
        version=version,
        description=_text(data, "description"),
        core=core,
        provides=provides,
        requires=_list(data, "requires"),
        dependencies=_list(data, "dependencies"),
        permissions=_list(data, "permissions"),
        path=Path(path),
    )


def core_compatible(spec: str, version: str = CONTRACT_VERSION) -> bool:
    if not spec:
        return True
    try:
        return SpecifierSet(spec).contains(version)
    except InvalidSpecifier:
        return False


def localized(value: dict[str, str], lang: str) -> str:
    if lang in value:
        return value[lang]
    if "en" in value:
        return value["en"]
    return next(iter(value.values()), "")
