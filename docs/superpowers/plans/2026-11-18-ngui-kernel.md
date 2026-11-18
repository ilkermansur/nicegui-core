# ngui Çekirdeği — Uygulama Planı (Plan 1/2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Plugin'leri git'ten çeken, sıraya dizen, yükleyen ve yöneten küçük çekirdeği (`ngui` paketi + CLI + Docker dosyaları) kurmak. Gerçek core plugin'leri yok; çekirdek test plugin'leriyle uçtan uca doğrulanır.

**Architecture:** `ngui/` paketi küçük, tek sorumluluklu modüllerden oluşur: config/lock, manifest, i18n, bus, roller (Protocol), loader, git işlemleri, manager, app (NiceGUI başlatma + kurtarma sayfası + yeniden başlatma), CLI ve şablon üretici. Plugin'ler `importlib` ile klasör yolundan yüklenir; rol plugin'lerinin `setup(ctx)` dönüş değeri rolün uygulamasıdır.

**Tech Stack:** Python 3.12, NiceGUI 4.x, `tomllib` + `tomli-w`, `packaging`, `git` (subprocess), `uv` (yoksa `pip`), pytest, Docker.

**Spec:** `docs/superpowers/specs/2026-11-18-nicegui-plugin-platform-design.md`

**Kapsam:** Bu plan yalnızca bu repo'yu (çekirdek) kapsar. `nicegui-core-plugins` reposu (layout-sidebar, storage-sqlite, auth-local, theme-default, store) **Plan 2**'dir ve bu plan bittikten sonra yazılır; o plan bu plandaki `CONTRACT.md` ve `ngui/roles.py`'yi girdi alır.

## Global Constraints

- Python `>=3.12`; `nicegui>=4,<5`. NiceGUI 4 yeni bir major sürüm: `ui.page`, `ui.run`, `app.storage`, `background_tasks` çağrılarını kurulu sürümün dokümanına göre doğrula.
- Durum dizini `NGUI_HOME` ortam değişkeni, yoksa `/data`.
- Sözleşme sürümü `CONTRACT_VERSION = "1.0"`; manifest'teki `core` alanı bir PEP 440 specifier'dır (ör. `">=1,<2"`).
- Plugin kimliği deseni `^[a-z][a-z0-9-]*$`. Ayrılmış kimlikler: `core`, `core-plugins`.
- Özellik plugin repo adı `nicegui-plugin-<id>`.
- Rol yükleme sırası tam olarak: `storage`, `auth`, `theme`, `layout`.
- Varsayılan dil `tr`, geri düşme `en`, sonra anahtarın kendisi.
- Hiçbir modül bir plugin'i adıyla import etmez; çekirdek kodu yalnızca `ngui.*` içindedir.
- Token (`GITHUB_TOKEN`) diske yazılmaz; git'e yalnızca ortam değişkeni üzerinden geçilir.
- Hedef: `ngui/` toplamı ~600 satırı geçmesin (testler hariç). Geçerse önce sadeleştir.
- Her görev kendi commit'iyle biter; commit mesajları İngilizce, `feat:`/`test:`/`chore:`/`docs:` önekli, sonu `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Bozuk `plugin.toml`** (TOML hatası, eksik `id`, kimlik/klasör uyuşmazlığı) → o plugin "bozuk" olur, uygulama açılır. *(Task 2 ve Task 6 testleri)*
2. **Etkin ama diskte olmayan plugin** (repo klasörü elle silinmiş) → "kurulu değil" sorunu olarak raporlanır, çökme yok. *(Task 6)*
3. **`ngui add` başarısız olursa** (repo yok, ağ hatası) → yarım klon klasörü kalmaz, config ve lock değişmez. *(Task 8)*
4. **Bir olay dinleyicisi hata fırlatırsa** → diğer dinleyiciler yine çalışır, `emit` hata fırlatmaz. *(Task 4)*
5. **Bayat PID dosyası** (uygulama çalışmıyor) → CLI komutu başarıyla biter, sinyal gönderilemediğini sessizce geçer. *(Task 10)*

---

## Dosya Haritası

```
pyproject.toml            paket, bağımlılıklar, `ngui` console script
ngui/__init__.py          CONTRACT_VERSION, KERNEL_DIR
ngui/__main__.py          `python -m ngui` → cli.main
ngui/config.py            Home (yollar), Config, LockEntry, okuma/yazma
ngui/manifest.py          Manifest, load_manifest, core_compatible, localized
ngui/i18n.py              I18n
ngui/bus.py               Bus, Services
ngui/roles.py             ROLE_ORDER, rol Protocol'leri
ngui/context.py           Kernel, Context
ngui/loader.py            discover, plan, load, LoadResult
ngui/gitops.py            git alt süreç sarmalayıcıları
ngui/manager.py           Manager, ManagerError, PluginStatus
ngui/app.py               run, restart, signal_app
ngui/recovery.py          kurtarma sayfası
ngui/cli.py               argparse CLI
ngui/scaffold.py          `ngui new` şablonu
ngui/locales/{tr,en}.toml çekirdeğin kendi metinleri (namespace "core")
tests/conftest.py         ortak fixture'lar (home, git kimliği, make_repo)
tests/fixtures/core-plugins/{storage-mem,auth-fake,theme-fake,layout-fake}/
tests/fixtures/plugins/{hello,needs-missing,boom}/
CONTRACT.md               plugin yazarı için tek doküman
Dockerfile, docker-compose.yml, .env.example, .dockerignore, README.md
```

---

### Task 1: Proje iskeleti ve `config`

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `ngui/__init__.py`, `ngui/config.py`, `tests/conftest.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `ngui.CONTRACT_VERSION: str = "1.0"`, `ngui.KERNEL_DIR: Path` (repo kökü)
  - `CORE_KEY = "core-plugins"`
  - `DEFAULT_ROLES = {"storage": "storage-sqlite", "auth": "auth-local", "theme": "theme-default", "layout": "layout-sidebar"}`
  - `DEFAULT_ENABLED = ["storage-sqlite", "auth-local", "theme-default", "layout-sidebar", "store"]`
  - `@dataclass Config(default_lang="tr", core_repo="", sources: list[str]=[], enabled: list[str]=DEFAULT_ENABLED kopyası, roles: dict[str,str]=DEFAULT_ROLES kopyası, links: dict[str,str]={})`
  - `@dataclass LockEntry(url: str, commit: str, previous: str = "")`
  - `class Home(root: Path)` — öznitelikler: `root`, `repos_dir = root/"repos"`, `pydeps_dir = root/"pydeps"`, `data_dir = root/"data"`, `config_path = root/"config.toml"`, `lock_path = root/"plugins.lock"`, `pid_path = root/"ngui.pid"`, `secret_path = root/"secret"`; metotlar: `load_config() -> Config`, `save_config(cfg: Config) -> None`, `load_lock() -> dict[str, LockEntry]`, `save_lock(lock: dict[str, LockEntry]) -> None`, `secret() -> str`
  - `home_from_env() -> Home` (`NGUI_HOME`, yoksa `/data`)
  - conftest fixture'ları: `home` (`Home(tmp_path / "home")`), autouse `git_identity` (`GIT_AUTHOR_NAME/EMAIL`, `GIT_COMMITTER_NAME/EMAIL` monkeypatch), `make_repo(src: Path, name: str) -> str` (src'yi `tmp_path/"remotes"/name` altına kopyalar, `git init -b main`, add, commit; yolu string döndürür — git bu yolu klon URL'i olarak kabul eder)

- [ ] **Step 1: Repo ve sanal ortam**

Run: `git init -b main && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'` (önce `pyproject.toml`: name `ngui`, `requires-python = ">=3.12"`, dependencies `nicegui>=4,<5`, `tomli-w>=1.0`, `packaging>=24`; optional `dev = ["pytest>=8"]`; `[project.scripts] ngui = "ngui.cli:main"`; package-data `ngui/locales/*.toml`). `.gitignore`: `.venv/`, `__pycache__/`, `.nicegui/`, `*.egg-info/`.
Expected: kurulum hatasız biter.

- [ ] **Step 2: Failing testler — `tests/test_config.py`**

```python
def test_missing_config_returns_defaults(home):
    cfg = home.load_config()
    assert cfg.default_lang == "tr"
    assert cfg.roles["layout"] == "layout-sidebar"
    assert "store" in cfg.enabled

def test_config_roundtrip(home):
    cfg = home.load_config(); cfg.enabled.append("ai"); cfg.links["ai"] = "/x"
    home.save_config(cfg)
    again = home.load_config()
    assert again.enabled[-1] == "ai" and again.links == {"ai": "/x"}

def test_lock_roundtrip(home):
    home.save_lock({"ai": LockEntry("u", "c2", "c1")})
    assert home.load_lock()["ai"] == LockEntry("u", "c2", "c1")

def test_secret_is_stable_and_private(home):
    s = home.secret()
    assert s == home.secret() and len(s) >= 32
    assert oct(home.secret_path.stat().st_mode)[-3:] == "600"

def test_home_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("NGUI_HOME", str(tmp_path))
    assert home_from_env().root == tmp_path
```

- [ ] **Step 3: Testlerin kırıldığını gör**

Run: `.venv/bin/pytest tests/test_config.py -v` — Expected: FAIL (ImportError).

- [ ] **Step 4: `ngui/__init__.py` ve `ngui/config.py`'yi yaz**

Yazma `tomli_w` ile; `save_*` gerekirse `root`'u oluşturur. Lock dosyası her anahtar için bir tablo. `secret()` yoksa `secrets.token_hex(32)` üretip `0o600` ile yazar.

- [ ] **Step 5: Testler geçer** — `.venv/bin/pytest tests/test_config.py -v` → PASS

- [ ] **Step 6: Commit** — `git add -A && git commit -m "chore: project skeleton and config/lock handling"`

---

### Task 2: `manifest`

**Files:**
- Create: `ngui/manifest.py`, `tests/test_manifest.py`

**Interfaces:**
- Consumes: `ngui.CONTRACT_VERSION`
- Produces:
  - `class ManifestError(Exception)`
  - `@dataclass Manifest(id: str, name: dict[str,str], version: str, description: dict[str,str], core: str, provides: str, requires: list[str], dependencies: list[str], permissions: list[str], path: Path)`
  - `load_manifest(path: Path, expected_id: str | None = None) -> Manifest` — `path` plugin klasörü. `name`/`description` düz string ise `{"en": s}` olur. Varsayılanlar: `provides=""`, listeler boş, `core=">=1,<2"`.
  - `core_compatible(spec: str, version: str = CONTRACT_VERSION) -> bool`
  - `localized(value: dict[str,str], lang: str) -> str` — `lang`, yoksa `en`, yoksa ilk değer, yoksa `""`.

- [ ] **Step 1: Failing testler**

```python
def write(tmp_path, text, folder="ai"):
    d = tmp_path / folder; d.mkdir(); (d / "plugin.toml").write_text(text); return d

def test_minimal_manifest(tmp_path):
    m = load_manifest(write(tmp_path, 'id = "ai"\nversion = "0.1.0"'))
    assert m.id == "ai" and m.provides == "" and m.requires == [] and m.core == ">=1,<2"

def test_bilingual_name(tmp_path):
    m = load_manifest(write(tmp_path, 'id="ai"\nversion="1"\nname={tr="AI Sohbet",en="AI Chat"}'))
    assert localized(m.name, "tr") == "AI Sohbet" and localized(m.name, "de") == "AI Chat"

@pytest.mark.parametrize("text", ['id = ', 'version = "1"', 'id = "Bad_Id"\nversion="1"', 'id="core"\nversion="1"'])
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
```

- [ ] **Step 2: Kırıldığını gör** — `.venv/bin/pytest tests/test_manifest.py -v` → FAIL

- [ ] **Step 3: `ngui/manifest.py`'yi yaz** — `tomllib` hatası, eksik `id`/`version`, desen dışı ya da ayrılmış id, bilinmeyen `provides` (`ROLE_ORDER` dışı; Task 5'te tanımlanana kadar `("storage","auth","theme","layout")` sabitini `ngui/roles.py`'den import et — Task 5 o dosyayı genişletir, şimdi sadece sabiti olan bir `roles.py` oluştur) hepsi `ManifestError`. `core_compatible` `packaging.specifiers.SpecifierSet` kullanır; boş spec her zaman uyumlu.

- [ ] **Step 4: Geçer** — PASS

- [ ] **Step 5: Commit** — `git commit -am "feat: plugin manifest parsing" ` (yeni dosyaları önce `git add`)

---

### Task 3: `i18n`

**Files:**
- Create: `ngui/i18n.py`, `ngui/locales/tr.toml`, `ngui/locales/en.toml` (şimdilik birer test anahtarı: `"hello" = "Merhaba {name}"` / `"Hello {name}"`), `tests/test_i18n.py`

**Interfaces:**
- Produces: `class I18n(default_lang: str = "tr")`
  - `load(namespace: str, locales_dir: Path) -> None` — `<lang>.toml` dosyalarını okur; klasör yoksa sessizce geçer; bozuk TOML'u loglar ve atlar.
  - `t(namespace: str, key: str, lang: str | None = None, **vars) -> str` — zincir: `lang or current_lang()` → `en` → `key`. `vars` varsa `str.format(**vars)`; format hatasında biçimlenmemiş metin.
  - `lang_getter: Callable[[], str | None] | None`, `lang_setter: Callable[[str], None] | None` — çekirdek (Task 10) bağlar.
  - `current_lang() -> str` — getter yoksa, `None` döndürürse ya da hata fırlatırsa `default_lang`.
  - `set_lang(lang: str) -> None` — `lang_setter(lang)` çağırır, sonra NiceGUI istemci bağlamı varsa `ui.navigate.reload()`; bağlam yoksa yalnızca setter.
  - `languages() -> list[str]` — yüklenen tüm dillerin sıralı listesi.

- [ ] **Step 1: Failing testler**

```python
@pytest.fixture
def i18n(tmp_path):
    d = tmp_path / "locales"; d.mkdir()
    (d / "tr.toml").write_text('"greet" = "Merhaba {name}"\n"only_tr" = "Yalnız"')
    (d / "en.toml").write_text('"greet" = "Hello {name}"\n"only_en" = "Only"')
    i = I18n(); i.load("demo", d); return i

def test_default_lang_is_tr(i18n):        assert i18n.t("demo", "greet", name="Ali") == "Merhaba Ali"
def test_explicit_lang(i18n):             assert i18n.t("demo", "greet", lang="en", name="Ali") == "Hello Ali"
def test_falls_back_to_en(i18n):          assert i18n.t("demo", "only_en") == "Only"
def test_falls_back_to_key(i18n):         assert i18n.t("demo", "nope") == "nope"
def test_namespaces_isolated(i18n):       assert i18n.t("other", "greet") == "greet"
def test_bad_format_vars(i18n):           assert i18n.t("demo", "greet") == "Merhaba {name}"
def test_getter_wins(i18n):
    i18n.lang_getter = lambda: "en"; assert i18n.current_lang() == "en"
def test_getter_error_uses_default(i18n):
    i18n.lang_getter = lambda: 1 / 0; assert i18n.current_lang() == "tr"
def test_set_lang_calls_setter(i18n):
    seen = []; i18n.lang_setter = seen.append; i18n.set_lang("en"); assert seen == ["en"]
def test_languages(i18n):                 assert i18n.languages() == ["en", "tr"]
```

- [ ] **Step 2: Kırıldığını gör** → FAIL
- [ ] **Step 3: `ngui/i18n.py`'yi yaz** (`set_lang` içindeki reload: `from nicegui import context`; `context.client` erişimi hata verirse reload'u atla).
- [ ] **Step 4: Geçer** → PASS
- [ ] **Step 5: Commit** — `feat: i18n with tr/en fallback`

---

### Task 4: `bus`

**Files:**
- Create: `ngui/bus.py`, `tests/test_bus.py`

**Interfaces:**
- Produces:
  - `class Bus` — `on(event: str, fn: Callable) -> None`, `off(event: str, fn: Callable) -> None`, `emit(event: str, data: Any = None) -> None`. Her dinleyici `fn(data)` ile çağrılır; hata fırlatan dinleyici loglanır, diğerleri çalışmaya devam eder. Dönüş değeri awaitable ise `nicegui.background_tasks.create(...)` ile zamanlanır (olay döngüsü yoksa coroutine kapatılır ve loglanır).
  - `class Services` — `provide(name: str, obj: Any) -> None` (aynı ad tekrar verilirse uyarı loglar ve üzerine yazar), `get(name: str) -> Any | None`.

- [ ] **Step 1: Failing testler**

```python
def test_emit_reaches_listeners_in_order():
    b, seen = Bus(), []
    b.on("x", lambda d: seen.append(("a", d))); b.on("x", lambda d: seen.append(("b", d)))
    b.emit("x", 1)
    assert seen == [("a", 1), ("b", 1)]

def test_emit_without_listeners_is_noop():
    Bus().emit("nothing")

def test_failing_listener_does_not_stop_others(caplog):
    b, seen = Bus(), []
    b.on("x", lambda d: 1 / 0); b.on("x", seen.append)
    b.emit("x", 5)
    assert seen == [5] and "ZeroDivisionError" in caplog.text

def test_off():
    b, seen = Bus(), []
    b.on("x", seen.append); b.off("x", seen.append); b.emit("x", 1)
    assert seen == []

def test_services():
    s = Services(); assert s.get("db") is None
    s.provide("db", 42); assert s.get("db") == 42

def test_service_override_warns(caplog):
    s = Services(); s.provide("db", 1); s.provide("db", 2)
    assert s.get("db") == 2 and "db" in caplog.text
```

- [ ] **Step 2: Kırıldığını gör** → FAIL
- [ ] **Step 3: `ngui/bus.py`'yi yaz**
- [ ] **Step 4: Geçer** → PASS
- [ ] **Step 5: Commit** — `feat: event bus and service registry`

---

### Task 5: Rol sözleşmeleri, `Kernel` ve `Context`

**Files:**
- Modify: `ngui/roles.py` (Task 2'deki sabiti genişlet)
- Create: `ngui/context.py`, `tests/test_context.py`

**Interfaces:**
- Produces (`ngui/roles.py`) — `typing.Protocol` sınıfları; spec §4.1'deki anlamla:
  - `ROLE_ORDER = ("storage", "auth", "theme", "layout")`
  - `class User(TypedDict): id: str; name: str; roles: list[str]`
  - `class PluginStore(Protocol)`: `get(key: str, default=None)`, `set(key: str, value) -> None`, `delete(key: str) -> None`, `list(prefix: str = "") -> list[str]`, `shared: "PluginStore"`, `for_user(user_id: str) -> "PluginStore"`
  - `class StorageRole(Protocol)`: `for_plugin(plugin_id: str) -> PluginStore`, `purge(plugin_id: str) -> None`
  - `class AuthRole(Protocol)`: `current_user() -> User`, `has(permission: str) -> bool`
  - `class ThemeRole(Protocol)`: `mode: str`, `set_mode(mode: str) -> None`, `card(title: str | None = None, actions: Callable | None = None)`, `kpi(label: str, value, icon: str | None = None, tone: str = "neutral")`, `page_header(title: str, description: str | None = None)`
  - `class LayoutRole(Protocol)`: `page(path: str, title: str, icon: str | None = None, permission: str | None = None) -> Callable`, `add(slot: str, builder: Callable[[], None]) -> None`
- Produces (`ngui/context.py`):
  - `@dataclass Kernel(home: Home, config: Config, bus: Bus, services: Services, i18n: I18n, roles: dict[str, Any] = {}, manager: Any = None, result: Any = None, restart: Callable[[], None] = lambda: None)`
  - `class Context(manifest: Manifest, kernel: Kernel)` — `id`, `manifest`, `path` (= `manifest.path`), `log` (`logging.getLogger(f"ngui.{id}")`), `bus`, `services`, `i18n`, `kernel`; `role(name: str) -> Any` (yüklenmemiş rol için `LookupError`), `storage` property (`role("storage").for_plugin(id)`), `t(key: str, **vars) -> str` (`i18n.t(id, key, **vars)`).

- [ ] **Step 1: Failing testler**

```python
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
```

- [ ] **Step 2: Kırıldığını gör** → FAIL
- [ ] **Step 3: `ngui/roles.py` ve `ngui/context.py`'yi yaz**
- [ ] **Step 4: Geçer** → PASS
- [ ] **Step 5: Commit** — `feat: role contracts, kernel and plugin context`

---

### Task 6: `loader` ve test plugin'leri

**Files:**
- Create: `ngui/loader.py`, `tests/test_loader.py`, `tests/fixtures/core-plugins/{storage-mem,auth-fake,theme-fake,layout-fake}/{plugin.toml,__init__.py}`, `tests/fixtures/plugins/hello/{plugin.toml,__init__.py,locales/tr.toml,locales/en.toml}`, `tests/fixtures/plugins/needs-missing/…` (`requires=["ghost"]`), `tests/fixtures/plugins/boom/…` (`setup` içinde `raise RuntimeError("boom")`)

Test plugin'leri bilerek minimaldir:
- `storage-mem`: `provides="storage"`; `setup` bellekte dict tabanlı bir `StorageRole` döndürür (kapsam anahtarı `(plugin_id, "local")`).
- `auth-fake`: `provides="auth"`; `current_user()` → `{"id": "local", "name": "admin", "roles": ["admin"]}`, `has` → `True`.
- `theme-fake`: `provides="theme"`; `mode="auto"`, parçalar `ui.card`/`ui.label` ile.
- `layout-fake`: `provides="layout"`; `page()` `ui.page(path)` kaydeder, önce `ui.label("LAYOUT-FAKE")` sonra içerik; `add()` bilinmeyen yuvayı yok sayar.
- `hello`: özellik plugin'i; `ctx.role("layout").page("/hello", ctx.t("title"))` altında `ui.label(ctx.t("greet"))`; locales: tr `"greet" = "Merhaba dünya"`, en `"greet" = "Hello world"`; ayrıca `ctx.services.provide("hello.ping", lambda: "pong")`.

**Interfaces:**
- Consumes: `Home`, `Config`, `load_manifest`, `core_compatible`, `ROLE_ORDER`, `Kernel`, `Context`
- Produces:
  - `@dataclass LoadResult(loaded: list[str], broken: dict[str, str], missing_roles: list[str])` — `broken` değerleri insan okunur sebep metnidir (İngilizce, kısa; ör. `"not installed"`, `"incompatible core: >=2"`, `"missing requirement: ghost"`, `"dependency cycle"`, `"setup failed: RuntimeError: boom"`, `"invalid manifest: …"`, `"role plugin returned nothing"`).
  - `discover(home: Home, cfg: Config) -> dict[str, Path]` — `repos/core-plugins/*/plugin.toml` klasörleri (anahtar klasör adı), `repos/<id>/plugin.toml` (anahtar `<id>`), sonra `cfg.links` (yolu `expanduser`; varsa üzerine yazar).
  - `plan(manifests: dict[str, Manifest], cfg: Config) -> tuple[list[str], dict[str, str]]` — yüklenecek küme = `cfg.enabled ∪ cfg.roles.values()`; rol tanımlayan ama o role atanmamış plugin sessizce dışarıda kalır; `requires` karşılanmayanlar tekrarlı biçimde düşer (bozuk bir bağımlılığa dayanan da bozuk); sıra: önce `ROLE_ORDER`'daki rol plugin'leri, sonra kalanlar topolojik (eşitlikte ada göre).
  - `load(kernel: Kernel) -> LoadResult` — `discover` → `load_manifest(path, expected_id=key)` (hata → broken) → `plan` → her plugin için `importlib.util.spec_from_file_location(f"ngui_plugins.{id.replace('-', '_')}", path/"__init__.py", submodule_search_locations=[str(path)])`, `sys.modules`'a kayıt, `i18n.load(id, path/"locales")`, `setup(Context(...))` `try` içinde. `provides` doluysa dönüş değeri `kernel.roles[provides]` olur. Bir rol plugin'i bozulursa ona `requires` ile bağlı olmayanlar yine yüklenir. Bitince `missing_roles` = `ROLE_ORDER`'da `kernel.roles`'ta olmayanlar. Sonuç `kernel.result`'a da yazılır.

- [ ] **Step 1: Failing testler** — yardımcı: `install_fixtures(home, *names)` fixture klasörlerini `home.repos_dir` altına kopyalar (core olanlar `core-plugins/` içine); `cfg.roles = {"storage":"storage-mem","auth":"auth-fake","theme":"theme-fake","layout":"layout-fake"}`.

```python
def test_loads_roles_in_order_then_features(kernel):
    kernel.config.enabled = ["hello"]
    r = load(kernel)
    assert r.loaded == ["storage-mem", "auth-fake", "theme-fake", "layout-fake", "hello"]
    assert r.missing_roles == [] and kernel.services.get("hello.ping")() == "pong"

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

def test_cycle(kernel_with_cycle):   # a requires b, b requires a (tmp fixture'ları testte yazılır)
    r = load(kernel_with_cycle)
    assert r.broken["a"] == r.broken["b"] == "dependency cycle"

def test_link_overrides_repo(kernel, tmp_path):
    dev = shutil.copytree(FIXTURES / "plugins" / "hello", tmp_path / "dev" / "hello")
    (dev / "locales" / "tr.toml").write_text('"greet" = "DEV"\n"title" = "Merhaba"')
    kernel.config.enabled = ["hello"]; kernel.config.links["hello"] = str(dev)
    load(kernel)
    assert kernel.i18n.t("hello", "greet") == "DEV"
```

- [ ] **Step 2: Kırıldığını gör** → FAIL
- [ ] **Step 3: Fixture plugin'lerini ve `ngui/loader.py`'yi yaz** (topolojik sıra için `graphlib.TopologicalSorter`; `CycleError` → döngüdeki düğümler bozuk).
- [ ] **Step 4: Geçer** → PASS
- [ ] **Step 5: Commit** — `feat: plugin loader with ordering and failure isolation`

---

### Task 7: `gitops`

**Files:**
- Create: `ngui/gitops.py`, `tests/test_gitops.py`

**Interfaces:**
- Produces:
  - `class GitError(Exception)` (mesaj git'in stderr'i)
  - `clone(url: str, dest: Path) -> str` — commit hash döndürür; hata olursa `dest`'i siler ve `GitError`.
  - `pull(dest: Path) -> str` — `git pull --ff-only`, yeni HEAD.
  - `checkout(dest: Path, commit: str) -> None` — `git checkout --detach <commit>` (pull'dan önce `git checkout main`/varsayılan dala dönmeyi `pull` kendisi yapar: `git checkout -` yerine `git symbolic-ref refs/remotes/origin/HEAD` ile varsayılan dalı bulur).
  - `head(dest: Path) -> str`
  - `exists(url: str) -> bool` — `git ls-remote --exit-code`.
  - Kimlik: `GITHUB_TOKEN` varsa her çağrıya ortam üzerinden `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=http.https://github.com/.extraheader`, `GIT_CONFIG_VALUE_0=AUTHORIZATION: basic <base64("x-access-token:"+token)>` eklenir; ayrıca `GIT_TERMINAL_PROMPT=0`.

- [ ] **Step 1: Failing testler** (`make_repo` ile yerel uzak repo)

```python
def test_clone_and_head(make_repo, tmp_path):
    url = make_repo(FIXTURES / "plugins" / "hello", "nicegui-plugin-hello")
    c = clone(url, tmp_path / "w")
    assert c == head(tmp_path / "w") and len(c) == 40

def test_clone_failure_leaves_nothing(tmp_path):
    with pytest.raises(GitError): clone(str(tmp_path / "nope"), tmp_path / "w")
    assert not (tmp_path / "w").exists()

def test_pull_then_checkout_back(make_repo, tmp_path):
    url = make_repo(FIXTURES / "plugins" / "hello", "r"); first = clone(url, tmp_path / "w")
    commit_change(url)                       # yardımcı: uzak repoya yeni commit
    second = pull(tmp_path / "w"); assert second != first
    checkout(tmp_path / "w", first); assert head(tmp_path / "w") == first
    assert pull(tmp_path / "w") == second    # detached'tan sonra pull tekrar çalışır

def test_exists(make_repo, tmp_path):
    assert exists(make_repo(FIXTURES / "plugins" / "hello", "r"))
    assert not exists(str(tmp_path / "nope"))

def test_token_goes_through_env_only(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t0k")
    env = _env()
    assert env["GIT_CONFIG_KEY_0"] == "http.https://github.com/.extraheader" and "t0k" not in env["GIT_CONFIG_VALUE_0"]
```

- [ ] **Step 2: Kırıldığını gör** → FAIL
- [ ] **Step 3: `ngui/gitops.py`'yi yaz** (`subprocess.run([...], capture_output=True, text=True, env=_env())`)
- [ ] **Step 4: Geçer** → PASS
- [ ] **Step 5: Commit** — `feat: git operations`

---

### Task 8: `manager` — kur, kaldır, aç/kapat, rol, link, durum

**Files:**
- Create: `ngui/manager.py`, `tests/test_manager.py`

**Interfaces:**
- Consumes: `Home`, `Config`, `LockEntry`, `CORE_KEY`, `gitops.*`, `loader.discover`, `loader.plan`, `load_manifest`
- Produces:
  - `class ManagerError(Exception)` — `__init__(self, key: str, **vars)`; `.key`, `.vars`. Anahtarlar `ngui/locales/*.toml`'da çevrilir (Task 11). Bu task'ta kullanılan anahtarlar: `err.not_found`, `err.already_installed`, `err.not_installed`, `err.is_core`, `err.fills_role`, `err.not_role_plugin`, `err.wrong_role`, `err.bad_path`, `err.git`.
  - `@dataclass PluginStatus(id: str, source: str, enabled: bool, role: str, commit: str, problem: str)` — `source ∈ {"core","repo","link"}`; `role` doldurduğu rol ya da `""`; `problem` `loader.plan`'ın sebebi ya da `""`.
  - `class Manager(home: Home)`:
    - `bootstrap() -> None` — config yoksa varsayılanı yazar (`core_repo` = `NGUI_CORE_REPO` ortam değişkeni ya da boş); `core_repo` doluysa ve `repos/core-plugins` yoksa klonlar ve lock'a `CORE_KEY` girdisini yazar. Klon hatası yutulur ve loglanır (kurtarma sayfası gösterecek).
    - `resolve(name_or_url: str) -> tuple[str, str]` — `://` içeriyorsa ya da var olan bir yolsa URL olarak alınır; id = son yol parçası, `.git` ve `nicegui-plugin-` atılmış. Değilse her `cfg.sources` girdisi için `https://{source}/nicegui-plugin-{name}` denenir, ilk `exists` olan döner; yoksa `err.not_found`.
    - `add(name_or_url: str) -> str` — zaten `repos/<id>` varsa `err.already_installed`; klon → `load_manifest(dest, expected_id=id)` (hata → klasörü sil, `ManifestError`'ı yeniden fırlat) → lock'a `LockEntry(url, commit)` → `enabled`'a ekle. Config/lock yalnızca her şey başarılıysa yazılır.
    - `remove(id: str) -> None` — core plugin ise `err.is_core`; rol dolduruyorsa `err.fills_role`; yoksa `err.not_installed`; klasörü sil, lock'tan ve `enabled`'dan çıkar, `links`'ten de çıkar. Veriye dokunmaz.
    - `enable(id)` / `disable(id)` — kurulu değilse `err.not_installed`; rol dolduran plugin'i `disable` → `err.fills_role`.
    - `use(role: str, id: str)` — plugin'in `provides` alanı `role` değilse `err.wrong_role`; `cfg.roles[role] = id`.
    - `link(id: str, path: str)` — `path/plugin.toml` yoksa `err.bad_path`; `cfg.links[id] = path` ve `enabled`'a ekle. `unlink(id)` — `links`'ten çıkarır.
    - `status() -> list[PluginStatus]` — `discover` + `plan`; ada göre sıralı.

- [ ] **Step 1: Failing testler** (fixture: `mgr` → `Manager(home)`, config'te `sources=[]`, roller fake; `core_url` → fake core-plugins'i `make_repo` ile hazırlanmış uzak repo)

```python
def test_bootstrap_clones_core(mgr, core_url, monkeypatch):
    monkeypatch.setenv("NGUI_CORE_REPO", core_url); mgr.bootstrap()
    assert (mgr.home.repos_dir / "core-plugins" / "layout-fake" / "plugin.toml").exists()
    assert mgr.home.load_lock()["core-plugins"].url == core_url

def test_bootstrap_with_unreachable_core_does_not_raise(mgr, monkeypatch, tmp_path):
    monkeypatch.setenv("NGUI_CORE_REPO", str(tmp_path / "nope")); mgr.bootstrap()
    assert not (mgr.home.repos_dir / "core-plugins").exists()

def test_add_by_url(mgr, hello_url):
    assert mgr.add(hello_url) == "hello"
    assert "hello" in mgr.home.load_config().enabled and mgr.home.load_lock()["hello"].commit

def test_resolve_by_name_tries_sources_in_order(mgr, monkeypatch):
    cfg = mgr.home.load_config(); cfg.sources = ["example.com/a", "github.com/me"]; mgr.home.save_config(cfg)
    monkeypatch.setattr("ngui.manager.gitops.exists", lambda u: u == "https://github.com/me/nicegui-plugin-hello")
    assert mgr.resolve("hello") == ("hello", "https://github.com/me/nicegui-plugin-hello")

def test_resolve_unknown_name(mgr, monkeypatch):
    monkeypatch.setattr("ngui.manager.gitops.exists", lambda u: False)
    with pytest.raises(ManagerError) as e: mgr.resolve("nope")
    assert e.value.key == "err.not_found"

def test_add_failure_changes_nothing(mgr, tmp_path):
    before = (mgr.home.load_config(), mgr.home.load_lock())
    with pytest.raises(ManagerError) as e: mgr.add(str(tmp_path / "nicegui-plugin-nope"))
    assert e.value.key == "err.git"
    assert (mgr.home.load_config(), mgr.home.load_lock()) == before
    assert not (mgr.home.repos_dir / "nope").exists()

def test_add_twice(mgr, hello_url):
    mgr.add(hello_url)
    with pytest.raises(ManagerError) as e: mgr.add(hello_url)
    assert e.value.key == "err.already_installed"

def test_remove(mgr, hello_url):
    mgr.add(hello_url); mgr.remove("hello")
    assert not (mgr.home.repos_dir / "hello").exists() and "hello" not in mgr.home.load_config().enabled

@pytest.mark.parametrize("pid,key", [("layout-fake", "err.is_core"), ("ghost", "err.not_installed")])
def test_remove_refusals(mgr_with_core, pid, key):
    with pytest.raises(ManagerError) as e: mgr_with_core.remove(pid)
    assert e.value.key == key

def test_disable_role_plugin_refused(mgr_with_core):
    with pytest.raises(ManagerError) as e: mgr_with_core.disable("layout-fake")
    assert e.value.key == "err.fills_role"

def test_use_checks_provides(mgr_with_core):
    with pytest.raises(ManagerError) as e: mgr_with_core.use("layout", "theme-fake")
    assert e.value.key == "err.wrong_role"

def test_link_and_unlink(mgr, tmp_path):
    dev = shutil.copytree(FIXTURES / "plugins" / "hello", tmp_path / "dev")
    mgr.link("hello", str(dev)); assert mgr.home.load_config().links["hello"] == str(dev)
    mgr.unlink("hello"); assert "hello" not in mgr.home.load_config().links

def test_status_reports_problems(mgr_with_core):
    cfg = mgr_with_core.home.load_config(); cfg.enabled.append("ghost"); mgr_with_core.home.save_config(cfg)
    st = {s.id: s for s in mgr_with_core.status()}
    assert st["ghost"].problem == "not installed" and st["layout-fake"].role == "layout" and st["layout-fake"].source == "core"
```

- [ ] **Step 2: Kırıldığını gör** → FAIL
- [ ] **Step 3: `ngui/manager.py`'nin bu bölümünü yaz** (`GitError` → `ManagerError("err.git", detail=str(e))`).
- [ ] **Step 4: Geçer** → PASS
- [ ] **Step 5: Commit** — `feat: plugin manager install/remove/enable/role/link`

---

### Task 9: `manager` — güncelle, geri al, bağımlılıklar, katalog, self-update

**Files:**
- Modify: `ngui/manager.py`
- Test: `tests/test_manager_update.py`

**Interfaces:**
- Produces (Manager'a eklenir):
  - `update(id: str) -> str` — `id == "core"` ise `CORE_KEY` reposu. Önce `pull`; sonra o repodaki tüm `plugin.toml`'lar okunur; herhangi biri `core_compatible` değilse eski commit'e `checkout` edilir ve `ManagerError("err.needs_self_update", plugin=<id>, spec=<core>)`. Başarılıysa `LockEntry(url, new, previous=old)` yazılır. Değişiklik yoksa `previous` güncellenmez. Yeni commit'i döndürür.
  - `rollback(id: str) -> str` — `previous` boşsa `ManagerError("err.no_previous")`; `checkout(previous)`, lock'ta `commit` ve `previous` yer değiştirir.
  - `sync_deps() -> bool` — yüklenecek plugin'lerin (`plan` sonrası) `dependencies` birleşimi sıralanır; `pydeps/.installed.json` ile aynıysa `False`. Değilse `self.run_cmd([...])` ile kurar: `uv` varsa `["uv", "pip", "install", "--target", pydeps, *specs]`, yoksa `[sys.executable, "-m", "pip", "install", "--target", pydeps, *specs]`; başarıda `.installed.json` yazılır, `True` döner; başarısızlıkta `ManagerError("err.deps", detail=stderr)`.
  - `run_cmd: Callable[[list[str]], subprocess.CompletedProcess]` — öznitelik, varsayılan `subprocess.run(..., capture_output=True, text=True)`; testler değiştirir.
  - `self_update(kernel_dir: Path) -> str` — `kernel_dir/.git` yoksa `ManagerError("err.self_update_docker")` (Docker'da çekirdek image'dadır; mesaj `git pull && docker compose build` önerir); varsa `pull(kernel_dir)`.
  - Yeni hata anahtarları: `err.needs_self_update`, `err.no_previous`, `err.deps`, `err.self_update_docker`.
  - `@dataclass CatalogEntry(id: str, description: str, url: str)`; `catalog() -> list[CatalogEntry]` — her `github.com/<owner>` kaynağı için `fetch_json(f"https://api.github.com/users/{owner}/repos?per_page=100")` (modül düzeyi `fetch_json(url) -> Any`, `urllib` ile; `GITHUB_TOKEN` varsa `Authorization: Bearer` başlığı); adı `nicegui-plugin-` ile başlayanlar; ağ/JSON hatası o kaynağı atlar ve loglar. GitHub dışı kaynaklar atlanır. Store (Plan 2) bunu kullanır.
  - Test yardımcısı (`tests/conftest.py`): `link_hello_with_deps(mgr, deps: list[str])` — hello fixture'ını tmp'ye kopyalar, `plugin.toml`'a `dependencies = [...]` ekler, `mgr.link("hello", path)` çağırır.

- [ ] **Step 1: Failing testler**

```python
def test_update_and_rollback(mgr, hello_url):
    mgr.add(hello_url); first = mgr.home.load_lock()["hello"].commit
    commit_change(hello_url); second = mgr.update("hello")
    assert second != first and mgr.home.load_lock()["hello"].previous == first
    assert mgr.rollback("hello") == first
    assert mgr.home.load_lock()["hello"] == LockEntry(hello_url, first, second)

def test_rollback_without_previous(mgr, hello_url):
    mgr.add(hello_url)
    with pytest.raises(ManagerError) as e: mgr.rollback("hello")
    assert e.value.key == "err.no_previous"

def test_core_update_refused_when_incompatible(mgr_with_core, core_url):
    old = mgr_with_core.home.load_lock()["core-plugins"].commit
    commit_change(core_url, "layout-fake/plugin.toml", append='\ncore = ">=2"')
    with pytest.raises(ManagerError) as e: mgr_with_core.update("core")
    assert e.value.key == "err.needs_self_update"
    assert head(mgr_with_core.home.repos_dir / "core-plugins") == old
    assert mgr_with_core.home.load_lock()["core-plugins"].commit == old

def test_sync_deps_installs_once(mgr_with_core, hello_url):
    calls = []; mgr_with_core.run_cmd = lambda cmd: calls.append(cmd) or CompletedProcess(cmd, 0, "", "")
    link_hello_with_deps(mgr_with_core, ["tinyhelper==1.0"])
    assert mgr_with_core.sync_deps() is True and calls[-1][-1] == "tinyhelper==1.0"
    assert mgr_with_core.sync_deps() is False and len(calls) == 1

def test_sync_deps_failure(mgr_with_core):
    mgr_with_core.run_cmd = lambda cmd: CompletedProcess(cmd, 1, "", "conflict")
    link_hello_with_deps(mgr_with_core, ["tinyhelper==1.0"])
    with pytest.raises(ManagerError) as e: mgr_with_core.sync_deps()
    assert e.value.key == "err.deps"

def test_catalog_lists_prefixed_repos(mgr, monkeypatch):
    cfg = mgr.home.load_config(); cfg.sources = ["github.com/me"]; mgr.home.save_config(cfg)
    monkeypatch.setattr("ngui.manager.fetch_json", lambda url: [
        {"name": "nicegui-plugin-ai", "description": "x", "html_url": "https://github.com/me/nicegui-plugin-ai"},
        {"name": "other-repo", "description": "", "html_url": "u"}])
    assert [c.id for c in mgr.catalog()] == ["ai"]

def test_catalog_survives_network_error(mgr, monkeypatch):
    cfg = mgr.home.load_config(); cfg.sources = ["github.com/me"]; mgr.home.save_config(cfg)
    monkeypatch.setattr("ngui.manager.fetch_json", lambda url: (_ for _ in ()).throw(OSError("offline")))
    assert mgr.catalog() == []

def test_self_update_without_git(mgr, tmp_path):
    with pytest.raises(ManagerError) as e: mgr.self_update(tmp_path)
    assert e.value.key == "err.self_update_docker"
```

- [ ] **Step 2: Kırıldığını gör** → FAIL
- [ ] **Step 3: Metotları yaz**
- [ ] **Step 4: Geçer** — `.venv/bin/pytest -v` (tüm suite) → PASS
- [ ] **Step 5: Commit** — `feat: update, rollback, dependency sync, catalog, self-update`

---

### Task 10: `app` — başlatma, kurtarma sayfası, yeniden başlatma

**Files:**
- Create: `ngui/app.py`, `ngui/recovery.py`, `tests/test_app.py`
- Modify: `ngui/locales/tr.toml`, `ngui/locales/en.toml` (kurtarma metinleri: `recovery.title`, `recovery.missing_role` ("Eksik rol: {role}" / "Missing role: {role}"), `recovery.broken`, `recovery.fix_hint`)

**Interfaces:**
- Consumes: `home_from_env`, `Manager`, `loader.load`, `Kernel`, `I18n`, `Bus`, `Services`
- Produces:
  - `run(home: Home | None = None) -> None` — sıra: `Manager(home).bootstrap()` → `sync_deps()` (hata loglanır, açılış sürer) → `sys.path.insert(0, pydeps)` → `I18n(cfg.default_lang)` + `i18n.load("core", ngui/locales)` → `Kernel(...)`, `kernel.manager = mgr`, `kernel.restart = restart` → `load(kernel)` → storage rolü varsa `i18n.lang_getter = lambda: roles["storage"].for_plugin("core").get("lang")`, `lang_setter` aynı anahtara yazar → `missing_roles` doluysa `recovery.mount(kernel)` → PID dosyası yazılır, `atexit` ile silinir → `signal.signal(SIGHUP, lambda *_: restart())` → `ui.run(host=NGUI_HOST or "127.0.0.1", port=int(NGUI_PORT or 8080), reload=False, show=False, title="ngui", storage_secret=home.secret())`.
  - `restart() -> NoReturn` — `os.execv(sys.executable, [sys.executable, "-m", "ngui", "run"])`.
  - `signal_app(home: Home) -> bool` — PID dosyasını okur, `os.kill(pid, SIGHUP)`; dosya yok/geçersiz/süreç yoksa `False`, asla hata fırlatmaz.
  - `recovery.mount(kernel: Kernel) -> None` — `@ui.page("/")` ve diğer her yol için 404 yerine aynı sayfa: başlık, her eksik rol için satır, `kernel.result.broken` listesi, ve `ngui list` / `ngui use <rol> <id>` / `ngui add <ad>` ipucu. Metinler `kernel.i18n.t("core", ...)` ile; layout/theme/auth/storage kullanılmaz.

Testler gerçek bir süreç başlatır (`python -m ngui run` henüz yok → bu task `ngui/__main__.py`'yi geçici olarak `from ngui.app import run; run()` çağıracak biçimde yazar; Task 11 onu CLI'ya bağlar).

- [ ] **Step 1: Failing testler** — yardımcı `start_app(env) -> (proc, base_url)` boş port seçer (`socket.bind(("127.0.0.1",0))`), `NGUI_HOME`, `NGUI_PORT`, `NGUI_CORE_REPO` ile `subprocess.Popen([sys.executable, "-m", "ngui", "run"])`, `/` 200 dönene kadar 20 sn yoklar; teardown'da süreci sonlandırır.

```python
def test_recovery_page_when_core_missing(tmp_path):
    proc, url = start_app({"NGUI_HOME": str(tmp_path / "h"), "NGUI_CORE_REPO": ""})
    html = urlopen(url + "/").read().decode()
    assert "Eksik rol: storage" in html and "ngui use" in html

def test_full_boot_with_fake_core_and_hello(tmp_path, core_url, hello_url):
    home = Home(tmp_path / "h")
    with env(NGUI_HOME=str(home.root), NGUI_CORE_REPO=core_url):
        m = Manager(home); m.bootstrap(); fake_roles(home); m.add(hello_url)
    proc, url = start_app({"NGUI_HOME": str(home.root)})
    html = urlopen(url + "/hello").read().decode()
    assert "LAYOUT-FAKE" in html and "Merhaba dünya" in html

def test_sighup_restarts_in_place(tmp_path, core_url):
    proc, url = start_app(...)                        # tam boot
    pid = int((tmp_path / "h" / "ngui.pid").read_text())
    assert signal_app(Home(tmp_path / "h")) is True
    wait_until_down_then_up(url)
    assert proc.poll() is None and proc.pid == pid    # execv: aynı PID

def test_signal_app_with_stale_pid(home):
    home.root.mkdir(parents=True); home.pid_path.write_text("999999")
    assert signal_app(home) is False

def test_signal_app_without_pidfile(home):
    assert signal_app(home) is False
```

(`fake_roles(home)` config'teki rolleri fake plugin'lere çevirir.)

- [ ] **Step 2: Kırıldığını gör** → FAIL
- [ ] **Step 3: `ngui/app.py`, `ngui/recovery.py`, geçici `ngui/__main__.py`'yi yaz.** Not: NiceGUI'nin ilk HTML'inde eleman metinleri gömülü değilse testler `"Merhaba dünya"` için sayfanın JSON yükünü arar — kurulu NiceGUI 4'te hangisi olduğunu kontrol et ve asserti ona göre yaz (metin aynı kalmalı).
- [ ] **Step 4: Geçer** → PASS
- [ ] **Step 5: Commit** — `feat: app runner, recovery page and in-place restart`

---

### Task 11: CLI

**Files:**
- Create: `ngui/cli.py`, `tests/test_cli.py`
- Modify: `ngui/__main__.py` (`raise SystemExit(main())`), `ngui/locales/{tr,en}.toml` (tüm `err.*` anahtarları + `cli.*` başarı mesajları; Task 3'teki `hello` test anahtarını sil)

**Interfaces:**
- Consumes: `Manager`, `ManagerError`, `ManifestError`, `signal_app`, `run`, `scaffold.new_plugin` (Task 12; bu task'ta `new` alt komutu yalnızca kaydedilir, Task 12 bağlar)
- Produces: `main(argv: list[str] | None = None) -> int`
  - Alt komutlar: `run`, `add <name_or_url>`, `remove <id>`, `update <id|core>`, `rollback <id|core>`, `enable <id>`, `disable <id>`, `use <role> <id>`, `link <id> <path>`, `unlink <id>`, `list`, `new <name> [--dir PATH]`, `self-update`.
  - Dil: `NGUI_LANG`, yoksa config'teki `default_lang`; metinler `i18n.t("core", ...)`.
  - Değiştiren her komut başarıda `sync_deps()` (yalnızca `add`/`update`/`rollback`/`enable`/`link` sonrası) ve `signal_app(home)` çağırır; sinyal gönderilemezse ek bir satır: `cli.not_running` ("Uygulama çalışmıyor; değişiklik bir sonraki açılışta geçerli olacak.").
  - Hata: `ManagerError`/`ManifestError` → çevrilmiş mesaj stderr'e, dönüş `1`. Başarı `0`.
  - `list` tablosu: `id`, kaynak, etkin (✓/–), rol, kısa commit (7), sorun.

- [ ] **Step 1: Failing testler**

```python
def test_add_list_remove(home_env, hello_url, capsys):
    assert main(["add", hello_url]) == 0
    assert main(["list"]) == 0 and "hello" in capsys.readouterr().out
    assert main(["remove", "hello"]) == 0

def test_error_is_translated_tr(home_env, capsys, monkeypatch):
    monkeypatch.setenv("NGUI_LANG", "tr")
    assert main(["remove", "ghost"]) == 1
    assert "kurulu değil" in capsys.readouterr().err

def test_error_is_translated_en(home_env, capsys, monkeypatch):
    monkeypatch.setenv("NGUI_LANG", "en")
    assert main(["remove", "ghost"]) == 1
    assert "not installed" in capsys.readouterr().err

def test_change_signals_running_app(home_env, hello_url, monkeypatch):
    seen = []; monkeypatch.setattr("ngui.cli.signal_app", lambda h: seen.append(h) or False)
    main(["add", hello_url]); assert len(seen) == 1

def test_every_err_key_has_tr_and_en():
    keys = set(re.findall(r'ManagerError\("(err\.[a-z_]+)"', (KERNEL_DIR / "ngui" / "manager.py").read_text()))
    for lang in ("tr", "en"):
        table = tomllib.loads((KERNEL_DIR / "ngui" / "locales" / f"{lang}.toml").read_text())
        assert keys <= set(table), (lang, keys - set(table))
```

(`home_env`: `NGUI_HOME`'u tmp'ye, `NGUI_CORE_REPO`'yu fake core'a ayarlar ve `bootstrap` + `fake_roles` çalıştırır.)

- [ ] **Step 2: Kırıldığını gör** → FAIL
- [ ] **Step 3: `ngui/cli.py`'yi yaz, locale dosyalarını doldur**
- [ ] **Step 4: Geçer** → tüm suite PASS
- [ ] **Step 5: Commit** — `feat: ngui CLI with tr/en messages`

---

### Task 12: `ngui new` şablonu ve `CONTRACT.md`

**Files:**
- Create: `ngui/scaffold.py`, `tests/test_scaffold.py`, `CONTRACT.md`
- Modify: `ngui/cli.py` (`new` alt komutunu bağla)

**Interfaces:**
- Produces: `new_plugin(name: str, parent: Path) -> Path` — `parent/f"nicegui-plugin-{name}"` oluşturur; içinde `plugin.toml` (iki dilli `name`/`description`, `version="0.1.0"`, `core=">=1,<2"`), `__init__.py` (`setup(ctx)`: `ctx.role("layout").page(f"/{name}", ctx.t("title"), icon="extension")` altında `ctx.role("theme").page_header(ctx.t("title"), ctx.t("description"))`), `locales/tr.toml`, `locales/en.toml` (`title`, `description`), `README.md` (kur/geliştir komutları), `.gitignore`; `git init -b main` + ilk commit. Geçersiz ad → `ManifestError`; hedef varsa `FileExistsError`.

`CONTRACT.md` (Türkçe, plugin yazarına yönelik, ~1-2 sayfa): klasör yapısı ve `plugin.toml` alanları; `setup(ctx)` ve `ctx`'nin tüm üyeleri; dört rolün metotları (`ngui/roles.py` ile birebir); rol plugin'inin `setup` dönüş değeri kuralı; bus/servis kuralları ve "asla başka plugin import etme"; i18n kuralları (sabit metin yok, tr+en zorunlu); tasarım kuralları (sabit renk yok, `tone` adları, CSS değişken adları spec §4.4'teki gibi); depolama kapsamları ve istek bağlamı kuralı; gateway plugin örüntüsü (spec §10); geliştirme döngüsü (`ngui new` → `ngui link` → push → `ngui unlink` → `ngui update`).

- [ ] **Step 1: Failing testler**

```python
def test_scaffold_creates_loadable_plugin(tmp_path, kernel):   # kernel: Task 6'daki fake rollerle
    path = new_plugin("notes", tmp_path)
    m = load_manifest(path, expected_id="notes")
    assert localized(m.name, "tr") and localized(m.name, "en")
    kernel.config.links["notes"] = str(path); kernel.config.enabled.append("notes")
    assert "notes" in load(kernel).loaded

def test_scaffold_is_git_repo(tmp_path):
    assert head(new_plugin("notes", tmp_path))

def test_scaffold_rejects_bad_name(tmp_path):
    with pytest.raises(ManifestError): new_plugin("Bad Name", tmp_path)

def test_contract_mentions_every_role_method():
    text = (KERNEL_DIR / "CONTRACT.md").read_text()
    for name in ["for_plugin", "purge", "for_user", "shared", "current_user", "has", "set_mode",
                 "card", "kpi", "page_header", "page", "add", "ctx.t", "ctx.services", "ctx.bus"]:
        assert name in text, name
```

(`theme-fake`'e `page_header` eklenmiş olmalı — Task 6'da tanımlandı.)

- [ ] **Step 2: Kırıldığını gör** → FAIL
- [ ] **Step 3: `ngui/scaffold.py` ve `CONTRACT.md`'yi yaz, CLI'ya bağla**
- [ ] **Step 4: Geçer** → PASS
- [ ] **Step 5: Commit** — `feat: plugin scaffold and contract documentation`

---

### Task 13: Docker

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `.env.example`, `.dockerignore`, `README.md`

Değerler (spec §10):
- `Dockerfile`: `python:3.12-slim`; `apt-get install -y --no-install-recommends git`; `pip install --no-cache-dir uv`; `COPY . /opt/ngui`; `uv pip install --system /opt/ngui`; `ENV NGUI_HOME=/data NGUI_HOST=0.0.0.0 NGUI_PORT=8080 PYTHONUNBUFFERED=1`; `VOLUME /data`; `EXPOSE 8080`; `CMD ["ngui", "run"]`.
- `docker-compose.yml`: tek servis `app` (`build: .`, `env_file: .env`, `ports: ["127.0.0.1:8080:8080"]`, `volumes: ["ngui-data:/data"]`, `restart: unless-stopped`); `volumes: { ngui-data: {} }`. Dosyada servis eklemenin nereye yapılacağını gösteren tek satırlık yorum.
- `.env.example`: `NGUI_CORE_REPO=https://github.com/<sahip>/nicegui-core-plugins`, `GITHUB_TOKEN=`, `NGUI_LANG=tr`.
- `.dockerignore`: `.venv`, `.git`, `tests`, `docs`, `__pycache__`, `.nicegui`.
- `README.md` (Türkçe, kısa): ne olduğu, `cp .env.example .env && docker compose up -d --build`, `docker compose exec app ngui list`, plugin geliştirme döngüsü, `CONTRACT.md` bağlantısı.

- [ ] **Step 1: Image'ı derle** — Run: `docker compose build` → Expected: başarılı.
- [ ] **Step 2: Kurtarma sayfasıyla ayağa kalktığını doğrula** — Run: `cp .env.example .env && sed -i '' 's#^NGUI_CORE_REPO=.*#NGUI_CORE_REPO=#' .env && docker compose up -d && sleep 8 && curl -s http://127.0.0.1:8080/ | grep -c "storage"` → Expected: `1` ya da daha büyük (Plan 2'ye kadar core plugin olmadığı için kurtarma sayfası beklenen davranıştır).
- [ ] **Step 3: CLI container içinde çalışıyor** — Run: `docker compose exec app ngui list` → Expected: çıkış kodu 0.
- [ ] **Step 4: Durum volume'da kalıcı** — Run: `docker compose exec app sh -c 'ls /data' && docker compose down && docker compose up -d && docker compose exec app ls /data/secret` → Expected: `secret` hâlâ var.
- [ ] **Step 5: Kapat** — `docker compose down`; `.env` commit edilmez (`.gitignore`'a ekle).
- [ ] **Step 6: Commit** — `chore: docker image and compose setup`

---

## Bitiş kontrolü

- [ ] `.venv/bin/pytest -v` → tümü PASS
- [ ] `wc -l ngui/*.py` → toplam ~600 civarı; çok aşıyorsa sadeleştirme görevi aç
- [ ] Spec §7'deki her CLI satırı için `ngui --help` çıktısında bir alt komut var
