import shutil

from ngui.bus import Bus, Services
from ngui.config import Config
from ngui.context import Kernel
from ngui.i18n import I18n
from ngui.loader import load

from conftest import FIXTURES


def test_loads_roles_in_order_then_features(kernel):
    kernel.config.enabled = ["hello"]
    r = load(kernel)
    assert r.loaded == ["storage-mem", "auth-fake", "theme-fake", "layout-fake", "hello"]
    assert r.missing_roles == [] and kernel.services.get("hello.ping")() == "pong"
    assert kernel.result is r


def test_failing_setup_is_isolated(kernel):
    kernel.config.enabled = ["boom", "hello"]
    r = load(kernel)
    assert "hello" in r.loaded and r.broken["boom"].startswith("setup failed: RuntimeError")


def test_unmet_requirement(kernel):
    kernel.config.enabled = ["needs-missing"]
    assert load(kernel).broken["needs-missing"] == "missing requirement: ghost"


def test_enabled_but_not_installed(kernel):
    kernel.config.enabled = ["ghost"]
    assert load(kernel).broken["ghost"] == "not installed"


def test_invalid_manifest_is_broken(kernel):
    (kernel.home.repos_dir / "hello" / "plugin.toml").write_text("id = ")
    kernel.config.enabled = ["hello"]
    assert load(kernel).broken["hello"].startswith("invalid manifest")


def test_incompatible_core(kernel):
    p = kernel.home.repos_dir / "hello" / "plugin.toml"
    p.write_text(p.read_text() + '\ncore = ">=2"')
    kernel.config.enabled = ["hello"]
    assert load(kernel).broken["hello"] == "incompatible core: >=2"


def test_missing_role_reported(kernel):
    del kernel.config.roles["layout"]
    assert load(kernel).missing_roles == ["layout"]


def test_cycle(kernel):
    for name, other in (("a", "b"), ("b", "a")):
        d = kernel.home.repos_dir / name
        d.mkdir(parents=True)
        (d / "plugin.toml").write_text(f'id = "{name}"\nversion = "1"\nrequires = ["{other}"]\n')
        (d / "__init__.py").write_text("def setup(ctx):\n    pass\n")
    kernel.config.enabled = ["a", "b"]
    r = load(kernel)
    assert r.broken["a"] == r.broken["b"] == "dependency cycle"


def test_link_overrides_repo(kernel, tmp_path):
    dev = shutil.copytree(FIXTURES / "plugins" / "hello", tmp_path / "dev" / "hello")
    (dev / "locales" / "tr.toml").write_text('"greet" = "DEV"\n"title" = "Merhaba"')
    kernel.config.enabled = ["hello"]
    kernel.config.links["hello"] = str(dev)
    load(kernel)
    assert kernel.i18n.t("hello", "greet") == "DEV"


def test_unassigned_role_plugin_is_skipped(kernel, install_fixtures):
    kernel.config.enabled = ["theme-fake"]
    kernel.config.roles["theme"] = "other"
    r = load(kernel)
    assert "theme-fake" not in r.loaded and "theme-fake" not in r.broken
