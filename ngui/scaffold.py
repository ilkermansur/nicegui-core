import shutil
from pathlib import Path

from ngui.gitops import GitError, git
from ngui.manifest import ID_PATTERN, RESERVED_IDS, ManifestError

_FILES = {
    "plugin.toml": '''id = "{name}"
name = {{ tr = "{name}", en = "{name}" }}
version = "0.1.0"
description = {{ tr = "{name} eklentisi", en = "The {name} plugin" }}
core = ">=1,<2"
''',
    "__init__.py": '''def setup(ctx):
    @ctx.role("layout").page("/{name}", lambda: ctx.t("title"), icon="extension")
    def page():
        ctx.role("theme").page_header(ctx.t("title"), ctx.t("description"))
''',
    "locales/tr.toml": 'title = "{name}"\ndescription = "{name} eklentisi"\n',
    "locales/en.toml": 'title = "{name}"\ndescription = "The {name} plugin"\n',
    "README.md": """# nicegui-plugin-{name}

Kur: `ngui add https://github.com/<kullanici>/nicegui-plugin-{name}`

Geliştir: `ngui link {name} .`, düzenle, push et, `ngui unlink {name}`, `ngui update {name}`.

Sözleşme: ngui deposundaki `CONTRACT.md`.
""",
    ".gitignore": "__pycache__/\n.env\n",
}


def new_plugin(name: str, parent: Path) -> Path:
    if not ID_PATTERN.fullmatch(name) or name in RESERVED_IDS:
        raise ManifestError(f"invalid or reserved plugin name '{name}'")
    dest = Path(parent) / f"nicegui-plugin-{name}"
    if dest.exists():
        raise FileExistsError(dest)
    try:
        for rel, text in _FILES.items():
            f = dest / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text.format(name=name), encoding="utf-8")
        git("init", "-b", "main", cwd=dest)
        git("add", "-A", cwd=dest)
        git("-c", "user.name=ngui", "-c", "user.email=ngui@localhost",
             "commit", "-m", "Initial plugin scaffold", cwd=dest)
    except (GitError, OSError) as e:
        shutil.rmtree(dest, ignore_errors=True)
        raise GitError(str(e)) from e
    return dest
