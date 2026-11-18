import pytest
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


def _plugin(kernel, name, toml_extra="", body="pass"):
    d = kernel.home.repos_dir / name
    d.mkdir(parents=True)
    (d / "plugin.toml").write_text(f'id = "{name}"\nversion = "1"\n{toml_extra}\n')
    (d / "__init__.py").write_text(f"def setup(ctx):\n    {body}\n")


def test_dependent_of_failed_setup_is_not_loaded(kernel):
    _plugin(kernel, "needs-boom", 'requires = ["boom"]')
    kernel.config.enabled = ["boom", "needs-boom"]
    r = load(kernel)
    assert "needs-boom" not in r.loaded and r.broken["needs-boom"] == "missing requirement: boom"


def test_role_requiring_unloaded_plugin_fails_honestly(kernel):
    p = kernel.home.repos_dir / "core-plugins" / "layout-fake" / "plugin.toml"
    p.write_text(p.read_text() + '\nrequires = ["hello"]')
    kernel.config.enabled = ["hello"]
    r = load(kernel)
    assert r.broken["layout-fake"] == "missing requirement: hello" and "layout-fake" not in r.loaded


def test_broken_role_keeps_independent_feature(kernel):
    (kernel.home.repos_dir / "core-plugins" / "theme-fake" / "__init__.py").write_text(
        "def setup(ctx):\n    raise RuntimeError('theme')\n")
    kernel.config.enabled = ["hello"]
    r = load(kernel)
    assert r.missing_roles == ["theme"] and "hello" in r.loaded


def test_plugin_calling_sys_exit_is_isolated(kernel):
    _plugin(kernel, "quitter", body="import sys; sys.exit(3)")
    kernel.config.enabled = ["quitter", "hello"]
    r = load(kernel)
    assert "hello" in r.loaded and r.broken["quitter"].startswith("setup failed: SystemExit")


def test_plugin_exiting_at_import_is_isolated(kernel):
    _plugin(kernel, "quitter2")
    (kernel.home.repos_dir / "quitter2" / "__init__.py").write_text("raise SystemExit(1)\n")
    kernel.config.enabled = ["quitter2", "hello"]
    r = load(kernel)
    assert "hello" in r.loaded and r.broken["quitter2"].startswith("setup failed: SystemExit")


def test_broken_plugins_are_logged(kernel, caplog):
    kernel.config.enabled = ["boom", "hello"]
    with caplog.at_level("ERROR", logger="ngui.loader"):
        load(kernel)
    assert "plugin boom not loaded: setup failed: RuntimeError" in caplog.text


@pytest.mark.parametrize("stmt", ["from . import helper", "from .helper import VALUE", "from .helper import *"])
def test_multi_file_plugin_relative_imports(kernel, stmt):
    _plugin(kernel, "multi", body="return None")
    d = kernel.home.repos_dir / "multi"
    (d / "helper.py").write_text("VALUE = 42\n")
    (d / "__init__.py").write_text(stmt + "\n\ndef setup(ctx):\n    pass\n")
    kernel.config.enabled = ["multi"]
    assert "multi" in load(kernel).loaded
