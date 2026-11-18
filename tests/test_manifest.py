import pytest

from ngui.manifest import ManifestError, core_compatible, load_manifest, localized


def write(tmp_path, text, folder="ai"):
    d = tmp_path / folder
    d.mkdir()
    (d / "plugin.toml").write_text(text)
    return d


def test_minimal_manifest(tmp_path):
    m = load_manifest(write(tmp_path, 'id = "ai"\nversion = "0.1.0"'))
    assert m.id == "ai" and m.provides == "" and m.requires == [] and m.core == ">=1,<2"


def test_bilingual_name(tmp_path):
    m = load_manifest(write(tmp_path, 'id="ai"\nversion="1"\nname={tr="AI Sohbet",en="AI Chat"}'))
    assert localized(m.name, "tr") == "AI Sohbet" and localized(m.name, "de") == "AI Chat"


@pytest.mark.parametrize("text", ['id = ', 'version = "1"', 'id = "Bad_Id"\nversion="1"', 'id="core"\nversion="1"',
                                  'id="core-plugins"\nversion="1"', 'id="ai\\n"\nversion="1"',
                                  'id="x"\nversion="1"\nprovides=5'])
def test_invalid_manifests(tmp_path, text):
    with pytest.raises(ManifestError):
        load_manifest(write(tmp_path, text))


def test_missing_file(tmp_path):
    (tmp_path / "x").mkdir()
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "x")


def test_id_must_match_expected(tmp_path):
    with pytest.raises(ManifestError):
        load_manifest(write(tmp_path, 'id="ai"\nversion="1"'), expected_id="notes")


def test_provides_must_be_known_role(tmp_path):
    with pytest.raises(ManifestError):
        load_manifest(write(tmp_path, 'id="x"\nversion="1"\nprovides="database"'))


@pytest.mark.parametrize("spec,ok", [(">=1,<2", True), (">=2", False), ("", True)])
def test_core_compatible(spec, ok):
    assert core_compatible(spec, "1.0") is ok


def test_undecodable_file(tmp_path):
    d = tmp_path / "ai"
    d.mkdir()
    (d / "plugin.toml").write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(ManifestError):
        load_manifest(d)
