import pytest

from ngui.bus import Bus, Services
from ngui.context import Context, Kernel
from ngui.i18n import I18n
from ngui.manifest import Manifest


def make_kernel(home):
    return Kernel(home=home, config=home.load_config(), bus=Bus(), services=Services(), i18n=I18n())


def test_role_lookup(home, tmp_path):
    k = make_kernel(home); k.roles["layout"] = "L"
    ctx = Context(Manifest("ai", {}, "1", {}, "", "", [], [], [], tmp_path), k)
    assert ctx.role("layout") == "L"
    with pytest.raises(LookupError): ctx.role("theme")


def test_storage_shortcut_scopes_by_plugin(home, tmp_path):
    k = make_kernel(home)
    class S:
        def for_plugin(self, pid): return f"store:{pid}"
    k.roles["storage"] = S()
    assert Context(Manifest("ai", {}, "1", {}, "", "", [], [], [], tmp_path), k).storage == "store:ai"


def test_t_uses_plugin_namespace(home, tmp_path):
    k = make_kernel(home); d = tmp_path / "loc"; d.mkdir()
    (d / "tr.toml").write_text('"k" = "v"'); k.i18n.load("ai", d)
    assert Context(Manifest("ai", {}, "1", {}, "", "", [], [], [], tmp_path), k).t("k") == "v"


def test_data_dir_is_per_plugin_and_created(home, tmp_path):
    k = make_kernel(home)
    d = Context(Manifest("ai", {}, "1", {}, "", "", [], [], [], tmp_path), k).data_dir
    assert d == home.data_dir / "plugins" / "ai" and d.is_dir()


def test_contract_is_1_1():
    from ngui.manifest import core_compatible
    assert core_compatible(">=1.1,<2") and core_compatible(">=1,<2")
