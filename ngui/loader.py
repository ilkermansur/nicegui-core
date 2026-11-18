import importlib.util
import sys
from dataclasses import dataclass, field
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from ngui.config import CORE_KEY, Config, Home
from ngui.context import Context, Kernel
from ngui.manifest import Manifest, ManifestError, core_compatible, load_manifest
from ngui.roles import ROLE_ORDER


@dataclass
class LoadResult:
    loaded: list[str] = field(default_factory=list)
    broken: dict[str, str] = field(default_factory=dict)
    missing_roles: list[str] = field(default_factory=list)


def discover(home: Home, cfg: Config) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for base in (home.repos_dir / CORE_KEY, home.repos_dir):
        if base.is_dir():
            for d in sorted(base.iterdir()):
                if (d / "plugin.toml").is_file():
                    found[d.name] = d
    for pid, link in cfg.links.items():
        found[pid] = Path(link).expanduser()
    return found


def read_manifests(home: Home, cfg: Config) -> tuple[dict[str, Manifest], dict[str, str]]:
    """Discovered, readable and core-compatible manifests, plus a reason for each bad one."""
    manifests, bad = {}, {}
    for pid, path in discover(home, cfg).items():
        try:
            m = load_manifest(path, expected_id=pid)
        except ManifestError as e:
            bad[pid] = f"invalid manifest: {e}"
            continue
        if core_compatible(m.core):
            manifests[pid] = m
        else:
            bad[pid] = f"incompatible core: {m.core}"
    return manifests, bad


def plan(manifests: dict[str, Manifest], cfg: Config) -> tuple[list[str], dict[str, str]]:
    broken: dict[str, str] = {}
    wanted = set(cfg.enabled) | set(cfg.roles.values())
    cand: dict[str, Manifest] = {}
    for pid in sorted(wanted):
        m = manifests.get(pid)
        if m is None:
            broken[pid] = "not installed"
        elif m.provides and cfg.roles.get(m.provides) != pid:
            continue  # role plugin not assigned to its role: silently skipped
        else:
            cand[pid] = m
    while True:
        unmet = {p: r for p, m in cand.items() for r in m.requires if r not in cand}
        if unmet:
            for p, r in unmet.items():
                broken[p] = f"missing requirement: {r}"
                del cand[p]
            continue
        ts = TopologicalSorter({p: m.requires for p, m in cand.items()})
        try:
            ts.prepare()
        except CycleError as e:
            for p in set(e.args[1]):
                broken[p] = "dependency cycle"
                cand.pop(p, None)
            continue
        break
    order = [cfg.roles[r] for r in ROLE_ORDER if cfg.roles.get(r) in cand]
    while ts.is_active():
        ready = sorted(ts.get_ready())
        order += [p for p in ready if p not in order]
        ts.done(*ready)
    return order, broken


def _import(manifest: Manifest):
    name = f"ngui_plugins.{manifest.id.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(
        name, manifest.path / "__init__.py", submodule_search_locations=[str(manifest.path)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def load(kernel: Kernel) -> LoadResult:
    cfg = kernel.config
    manifests, bad = read_manifests(kernel.home, cfg)
    order, broken = plan(manifests, cfg)
    result = LoadResult(broken={p: bad.get(p, why) for p, why in broken.items()})
    for pid in order:
        m = manifests[pid]
        failed = next((r for r in m.requires if r not in result.loaded), None)
        if failed:
            result.broken[pid] = f"missing requirement: {failed}"
            continue
        try:
            module = _import(m)
            kernel.i18n.load(pid, m.path / "locales")
            value = module.setup(Context(m, kernel))
        except Exception as e:
            result.broken[pid] = f"setup failed: {type(e).__name__}: {e}"
            continue
        if m.provides:
            if value is None:
                result.broken[pid] = "role plugin returned nothing"
                continue
            kernel.roles[m.provides] = value
        result.loaded.append(pid)
    result.missing_roles = [r for r in ROLE_ORDER if r not in kernel.roles]
    kernel.result = result
    return result
