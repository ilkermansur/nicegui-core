import pytest

from ngui.i18n import I18n


@pytest.fixture
def i18n(tmp_path):
    d = tmp_path / "locales"
    d.mkdir()
    (d / "tr.toml").write_text('"greet" = "Merhaba {name}"\n"only_tr" = "Yalnız"')
    (d / "en.toml").write_text('"greet" = "Hello {name}"\n"only_en" = "Only"')
    i = I18n()
    i.load("demo", d)
    return i


def test_default_lang_is_tr(i18n):
    assert i18n.t("demo", "greet", name="Ali") == "Merhaba Ali"


def test_explicit_lang(i18n):
    assert i18n.t("demo", "greet", lang="en", name="Ali") == "Hello Ali"


def test_falls_back_to_en(i18n):
    assert i18n.t("demo", "only_en") == "Only"


def test_falls_back_to_key(i18n):
    assert i18n.t("demo", "nope") == "nope"


def test_namespaces_isolated(i18n):
    assert i18n.t("other", "greet") == "greet"


def test_bad_format_vars(i18n):
    assert i18n.t("demo", "greet") == "Merhaba {name}"


def test_getter_wins(i18n):
    i18n.lang_getter = lambda: "en"
    assert i18n.current_lang() == "en"


def test_getter_none_uses_default(i18n):
    i18n.lang_getter = lambda: None
    assert i18n.current_lang() == "tr"


def test_getter_error_uses_default(i18n):
    i18n.lang_getter = lambda: 1 / 0
    assert i18n.current_lang() == "tr"


def test_set_lang_calls_setter(i18n):
    seen = []
    i18n.lang_setter = seen.append
    i18n.set_lang("en")
    assert seen == ["en"]


def test_languages(i18n):
    assert i18n.languages() == ["en", "tr"]


def test_missing_dir_and_broken_toml(tmp_path):
    i = I18n()
    i.load("x", tmp_path / "nope")
    d = tmp_path / "l"
    d.mkdir()
    (d / "tr.toml").write_text("= broken")
    i.load("y", d)
    assert i.t("y", "k") == "k"
