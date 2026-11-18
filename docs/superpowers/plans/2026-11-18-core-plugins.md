# Core Plugin'ler — Uygulama Planı (Plan 2/2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `nicegui-core-plugins` reposunu doldurmak: `storage-sqlite`, `auth-local`, `theme-default`, `layout-sidebar`, `store`. Hepsi iki dilli. Uygulama bu repoyla açıldığında referans ekrandaki tasarım dilinde çalışan bir kabuk ve plugin mağazası çıkar.

**Architecture:** Her plugin, repo kökünde bir klasördür: `plugin.toml` + `__init__.py` + `locales/{tr,en}.toml`. Rol plugin'lerinde `setup(ctx)` rolün uygulamasını döndürür. Testler çekirdeğin kendi `loader.load` fonksiyonunu ve gerçek bir `python -m ngui run` sürecini kullanır. Plugin'ler `config.links` ile doğrudan çalışma klasöründen yüklenir.

**Tech Stack:** Python 3.12, NiceGUI 4.x, `sqlite3` (stdlib), `ngui` çekirdeği (bu makinede `../n_gui`, editable kurulum), pytest.

**Spec:** `docs/superpowers/specs/2026-11-18-nicegui-plugin-platform-design.md` (çekirdek reposunda). Sözleşme: `CONTRACT.md` ve `ngui/roles.py` (çekirdek reposunda). Tasarım referansı: `docs/design/reference-dashboard.png`.

## Konumlar

- Çekirdek reposu: `/Users/ilkermansur/Desktop/n_gui` (remote `github.com/ilkermansur/nicegui-core`, dal `main`). Task 0 burada çalışır, kendi dalında: `feat/contract-tweaks`.
- Core plugin reposu: `/Users/ilkermansur/Desktop/nicegui-core-plugins` (yeni klasör, remote `https://github.com/ilkermansur/nicegui-core-plugins.git`, boş). Task 1–7 burada, dal `main` üzerinde çalışır. Repo yeni ve boş olduğu için ilk geliştirme doğrudan `main` dalında yapılır. Push, plan sonunda kullanıcı onayıyla yapılır.

## Global Constraints

- Plugin klasör adları ve id'leri tam olarak şunlar: `storage-sqlite`, `auth-local`, `theme-default`, `layout-sidebar`, `store`. Kök dizindeki klasör adı id ile aynıdır. Çekirdeğin `DEFAULT_ROLES` ve `DEFAULT_ENABLED` sabitleri bu adları kullanır.
- Her `plugin.toml` dosyasında şunlar olur: `version = "0.1.0"`, `core = ">=1,<2"`, ve iki dilli `name` ile `description` (`{ tr = "...", en = "..." }`).
- Rol plugin'lerinde `provides` alanı doludur: `storage`, `auth`, `theme`, `layout`. `store` bir özellik plugin'idir ve `permissions = ["store.manage"]` tanımlar.
- Her plugin'in `locales/tr.toml` ve `locales/en.toml` dosyaları tam ve aynı anahtar kümesine sahiptir. Noktalı anahtarlar tırnak içinde yazılır. Arayüzde sabit metin yoktur.
- Bir plugin başka bir plugin'i import etmez. Erişim yalnızca `ctx.role(...)`, `ctx.services` ve `ctx.bus` üzerindendir. `store`, çekirdeğin `ctx.kernel` alanını kullanabilir (Task 0'da sözleşmeye eklenir).
- Sabit renk kodu (hex, `rgb()`) yalnızca `theme-default` içinde bulunabilir. Diğer plugin'ler `var(--ngui-*)` değişkenlerini ve `tone` adlarını kullanır.
- Tasarım dili spec §4.4'e uyar: açık gri zemin, 1px kenarlıklı beyaz kartlar, gölge neredeyse yok, yoğun ama ferah düzen, dar ikon menü, ince ayırıcılar.
- Kod kısa ve basit tutulur. Hedef: her plugin'in `__init__.py` dosyası 200 satırı geçmez, `layout-sidebar` ve `store` için sınır 250 satırdır.
- Commit mesajları İngilizce olur, `feat:`/`test:`/`chore:`/`docs:` önekiyle yazılır. Mesajın son satırı commit'i yazan modelin `Co-Authored-By` satırıdır.

## Review Focus

1. **İstek bağlamı dışında storage erişimi.** Zamanlayıcıdan, bus dinleyicisinden ya da `setup` içinden `ctx.storage` çağrılırsa açık bir hata verilir. `.shared` ve `.for_user(id)` çalışmaya devam eder. Çekirdeğin dil okuyucusu bu hatada varsayılan dile düşer. *(Task 2)*
2. **Farklı yuvaları olan bir layout'a gönderilen bilinmeyen yuva.** `layout.add("sidebar", ...)` gibi bir çağrı sessizce yok sayılır, sayfa bozulmaz. *(Task 5)*
3. **Yetkisi olmayan sayfa.** Kullanıcının yetkisi olmayan bir sayfa menüde görünmez. Adresi doğrudan açılırsa bir "yetkiniz yok" mesajı çıkar, hata dökümü gösterilmez. *(Task 5)*
4. **Mağaza işlemi başarısız olursa.** Ağ ya da git hatası olduğunda çeviriyle bir bildirim gösterilir. Uygulama yeniden başlatılmaz, config dosyası değişmez. *(Task 6)*
5. **Dil ya da tema değişince sayfa yenilenir.** Menü başlıkları, sayfa başlıkları ve bileşen metinleri yeni dilde gelir, tema seçimi kullanıcı bazında kalıcıdır. *(Task 4, Task 5)*

---

## Dosya Haritası

```
n_gui/ (çekirdek, Task 0)
  ngui/roles.py            LayoutRole.page: title str | Callable[[], str]
  ngui/scaffold.py         şablon başlığı lambda ile
  CONTRACT.md              title callable notu + "sistem plugin'leri: ctx.kernel"
  tests/test_scaffold.py   (var olan testler geçmeye devam eder)

nicegui-core-plugins/
  README.md                ne olduğu, plugin listesi, geliştirme
  pyproject.toml           yalnızca test/dev yapılandırması (paket değil)
  .gitignore
  tests/conftest.py        make_kernel, start_app, plugin yolu sabitleri
  tests/test_storage.py  tests/test_auth.py  tests/test_theme.py
  tests/test_layout.py   tests/test_store.py tests/test_e2e.py tests/test_locales.py
  storage-sqlite/{plugin.toml,__init__.py,locales/}
  auth-local/{…}
  theme-default/{…}
  layout-sidebar/{…}
  store/{…}
```

---

### Task 0: Çekirdekte sözleşme düzeltmeleri (n_gui reposu)

**Neden:** Menü başlıkları `setup` anında `ctx.t(...)` ile sabitlenirse dil değişince eski dilde kalır. Mağazanın da çekirdeğin plugin yöneticisine erişmesi gerekir.

**Files:**
- Modify: `ngui/roles.py` (`LayoutRole.page` imzası), `ngui/scaffold.py` (şablon `__init__.py` dosyası), `CONTRACT.md` (§2 ve §3), `tests/test_scaffold.py` (gerekirse)

**Interfaces:**
- Produces:
  - `LayoutRole.page(path: str, title: str | Callable[[], str], icon: str | None = None, permission: str | None = None) -> Callable`. Layout, callable bir başlığı her çizimde yeniden çağırır.
  - CONTRACT §2'ye eklenecek satır: `ctx.kernel` yalnızca sistem plugin'leri (`store`) içindir. Alanları şunlardır: `manager` (`ngui.manager.Manager`), `restart()` ve `result` (`LoadResult`). Özellik plugin'leri bunu kullanmaz.
  - CONTRACT §3 örneği ve şablon şu biçimi kullanır: `page("/x", lambda: ctx.t("title"), ...)`.

- [ ] **Step 1:** Run `git checkout -b feat/contract-tweaks`.
- [ ] **Step 2: Failing test.** `tests/test_scaffold.py` dosyasına ekle:
```python
def test_scaffold_title_is_lazy(tmp_path):
    src = (new_plugin("notes", tmp_path) / "__init__.py").read_text()
    assert 'lambda: ctx.t("title")' in src
```
- [ ] **Step 3:** Run `.venv/bin/pytest tests/test_scaffold.py -v` → FAIL.
- [ ] **Step 4:** Değişiklikleri yap: `roles.py` imzası, şablon ve CONTRACT §2/§3. Ayrıca `tests/fixtures/core-plugins/layout-fake` callable başlığı kabul etsin (fixture başlığı göstermiyor, değişiklik gerekmiyorsa dokunma).
- [ ] **Step 5:** Run `.venv/bin/pytest -q` → hepsi PASS.
- [ ] **Step 6: Commit.** `docs: lazy page titles and ctx.kernel for system plugins`. Ardından `git checkout main && git merge --ff-only feat/contract-tweaks && git branch -d feat/contract-tweaks`. **Push yok.** Push plan sonunda yapılır.

---

### Task 1: Repo iskeleti ve test altyapısı

**Files (nicegui-core-plugins):**
- Create: `README.md`, `pyproject.toml`, `.gitignore`, `tests/conftest.py`, `tests/test_locales.py`

**Interfaces:**
- Produces (`tests/conftest.py`):
  - `REPO = Path(__file__).resolve().parent.parent`; `PLUGINS = ["storage-sqlite", "auth-local", "theme-default", "layout-sidebar", "store"]`
  - `REAL_ROLES = {"storage": "storage-sqlite", "auth": "auth-local", "theme": "theme-default", "layout": "layout-sidebar"}`
  - fixture `home(tmp_path) -> ngui.config.Home`
  - `make_kernel(home, plugins: list[str], roles: dict[str, str]) -> ngui.context.Kernel`. Config'e `links = {p: str(REPO/p) for p in plugins}` yazar, ayrıca `enabled = plugins` ve `roles = roles`. Kernel'i `app.run` ile aynı biçimde kurar: `I18n("tr")`, `i18n.load("core", LOCALES_DIR)`, `Bus`, `Services`. `loader.load(kernel)` çağrısını test yapar.
  - `start_app(home, plugins, roles, env=None) -> tuple[subprocess.Popen, str]`. Config'i `make_kernel` gibi yazar ve `python -m ngui run` komutunu `NGUI_HOME`, `NGUI_PORT` (boş port) ve `NGUI_CORE_REPO=""` ile başlatır. Yanıt gelene kadar 20 saniye bekler. Logu `tmp_path/app.log` dosyasına yazar, sunucu ayağa kalkmazsa assert mesajına ekler. Teardown süreci kapatır. Bu fonksiyon çekirdeğin `tests/test_app.py` içindeki yardımcısının kopyasıdır. `PYTEST_CURRENT_TEST` alt sürece geçirilmez.
  - `fetch(url) -> str`: HTTP gövdesi, NiceGUI 4'teki JSON yükü dahil.
- `pyproject.toml`: `[tool.pytest.ini_options] testpaths = ["tests"]`. Paket tanımı yoktur.
- `tests/test_locales.py`:
```python
@pytest.mark.parametrize("plugin", PLUGINS)
def test_locales_complete_and_equal(plugin):
    tr = tomllib.loads((REPO / plugin / "locales" / "tr.toml").read_text())
    en = tomllib.loads((REPO / plugin / "locales" / "en.toml").read_text())
    assert tr and set(tr) == set(en)
    assert all(isinstance(v, str) for v in [*tr.values(), *en.values()])

@pytest.mark.parametrize("plugin", PLUGINS)
def test_manifest_valid(plugin):
    m = load_manifest(REPO / plugin, expected_id=plugin)
    assert m.version == "0.1.0" and m.name.get("tr") and m.name.get("en")

def test_no_hex_colors_outside_theme():
    for p in PLUGINS:
        if p == "theme-default": continue
        for f in (REPO / p).rglob("*.py"):
            assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgb\(", f.read_text()), f

def test_no_cross_plugin_imports():
    for p in PLUGINS:
        for f in (REPO / p).rglob("*.py"):
            assert not re.search(r"^\s*(from|import)\s+ngui_plugins", f.read_text(), re.M), f
```
  Plugin klasörleri henüz yok. Bu testler her task'ta kendi plugin'i için yeşile döner. Bu task'ta parametre listesi `PLUGINS` sabitine bağlıdır. Henüz var olmayan plugin'ler için `pytest.skip` kullan (`if not (REPO/plugin).exists(): pytest.skip()`).

- [ ] **Step 1: Repo'yu kur.** `mkdir /Users/ilkermansur/Desktop/nicegui-core-plugins && cd` ile oraya geç, `git init -b main` çalıştır, `python3 -m venv .venv` ile ortam oluştur, sonra `.venv/bin/pip install -e /Users/ilkermansur/Desktop/n_gui[dev]`. `.gitignore` dosyasına `.venv/`, `__pycache__/`, `.nicegui/`, `.pytest_cache/`, `.superpowers/` girer.
- [ ] **Step 2:** `conftest.py` ve `test_locales.py` dosyalarını yaz. Run `.venv/bin/pytest -q` → hepsi skipped, hata yok.
- [ ] **Step 3:** README (Türkçe, kısa) şunları içerir: repo ne işe yarar, beş plugin'in tablosu (id, rol, ne yapar), çekirdek sözleşmesine bağlantı (`https://github.com/ilkermansur/nicegui-core/blob/main/CONTRACT.md`) ve yerel geliştirme komutları (`ngui link <id> <yol>`).
- [ ] **Step 4: Commit.** `chore: repo skeleton and test harness`

---

### Task 2: `storage-sqlite`

**Files:** `storage-sqlite/{plugin.toml,__init__.py,locales/tr.toml,locales/en.toml}`, `tests/test_storage.py`

**Interfaces:**
- Consumes: `ctx.kernel.home.data_dir` (DB yolu) ve çağrı anında `ctx.role("auth").current_user()["id"]`.
- Produces: `setup(ctx) -> SqliteStorage`.
  - `SqliteStorage(db_path: Path, user_id: Callable[[], str])`. `user_id` her çağrıda çözülür.
  - `SqliteStorage.for_plugin(pid) -> Store`, `SqliteStorage.purge(pid) -> None`.
  - `Store` sınıfının metotları `get(key, default=None)`, `set(key, value)`, `delete(key)` ve `list(prefix="") -> list[str]` (sıralı). Öznitelikleri `shared` ve `for_user(uid)`.
  - Kapsam değerleri: `"user:<id>"` (varsayılan; kullanıcı çağrı anında çözülür), `"user:<uid>"` (`for_user`) ve `"shared"`.
  - Şema: `CREATE TABLE IF NOT EXISTS kv(plugin TEXT, scope TEXT, key TEXT, value TEXT, PRIMARY KEY(plugin, scope, key))`. Değerler JSON olarak saklanır (`json.dumps(..., ensure_ascii=False)`).
  - DB dosyası `data_dir/"storage.sqlite3"`, gerekirse klasörü oluşturur. Bağlantı `check_same_thread=False` ile açılır, erişim `threading.Lock` ile korunur, her yazmadan sonra `commit` yapılır.
  - **İstek bağlamı kuralı:** Varsayılan kapsamda kullanıcı çözülürken NiceGUI slot yığını boşsa (`nicegui.slot.Slot.get_stack()` boş) `StorageContextError(RuntimeError)` fırlatılır. Mesaj `ctx.t("err.no_request")` metnidir. `shared` ve `for_user` bu kontrolü yapmaz.
  - Testlerde bağlam kontrolü değiştirilebilir olsun: modül düzeyinde `in_request: Callable[[], bool]` tanımlanır, testler bunu monkeypatch eder.
- locales: `"err.no_request"`. tr: `"Kullanıcı verisine yalnızca bir sayfa isteği içinde erişilebilir; .shared veya .for_user(id) kullanın."` en: `"User data is only available inside a page request; use .shared or .for_user(id)."`

- [ ] **Step 1: Failing tests** (`make_kernel(home, ["storage-sqlite", "auth-local"], {"storage": "storage-sqlite", "auth": "auth-local"})` çağrısı Task 3'e bağlıdır. Bu task'ta `auth-local` henüz yoktur. Testlerde storage'ı doğrudan `SqliteStorage(tmp/"db", lambda: "u1")` ile kur. Loader testi Task 3'te eklenir.)
```python
def test_roundtrip_and_types(store):           # store = SqliteStorage(...).for_plugin("p"); in_request=True
    store.set("a", {"x": [1, "ğ"]}); assert store.get("a") == {"x": [1, "ğ"]}
    assert store.get("missing", 7) == 7
def test_list_prefix_sorted(store):
    for k in ["b2", "a", "b1"]: store.set(k, 1)
    assert store.list("b") == ["b1", "b2"] and store.list() == ["a", "b1", "b2"]
def test_delete(store): store.set("a", 1); store.delete("a"); assert store.get("a") is None
def test_scopes_isolated(storage):             # storage = SqliteStorage(path, lambda: current["id"])
    p = storage.for_plugin("p"); p.set("k", "u1")
    p.shared.set("k", "shared"); p.for_user("u2").set("k", "u2")
    assert p.get("k") == "u1" and p.shared.get("k") == "shared" and p.for_user("u2").get("k") == "u2"
    assert storage.for_plugin("other").get("k") is None
def test_user_resolved_per_call(storage, current):
    p = storage.for_plugin("p"); p.set("k", 1); current["id"] = "u2"; assert p.get("k") is None
def test_outside_request_raises(storage, monkeypatch):
    monkeypatch.setattr(mod, "in_request", lambda: False)
    with pytest.raises(RuntimeError): storage.for_plugin("p").get("k")
    storage.for_plugin("p").shared.set("k", 1)          # shared works
    storage.for_plugin("p").for_user("u1").set("k", 1)  # for_user works
def test_purge(storage):
    storage.for_plugin("p").shared.set("k", 1); storage.for_plugin("q").shared.set("k", 1)
    storage.purge("p")
    assert storage.for_plugin("p").shared.get("k") is None and storage.for_plugin("q").shared.get("k") == 1
def test_persists_across_instances(tmp_path):
    SqliteStorage(tmp_path / "s.db", lambda: "u").for_plugin("p").shared.set("k", 1)
    assert SqliteStorage(tmp_path / "s.db", lambda: "u").for_plugin("p").shared.get("k") == 1
```
  Fixture'lar test dosyasında tanımlanır: `current` → `{"id": "u1"}`; `storage` → `SqliteStorage(tmp_path/"s.db", lambda: current["id"])`; `store` → `storage.for_plugin("p")`. Hepsinde `in_request` True olarak monkeypatch'lenir (autouse). Plugin modülünü test içinde içe aktarmak için `conftest.py` dosyasına `import_plugin(name) -> ModuleType` yardımcısını ekle: `importlib.util.spec_from_file_location` ile `REPO/name/__init__.py` yolunu, modül adı `cp_<name_underscored>` olacak şekilde yükler.
- [ ] **Step 2:** Run `.venv/bin/pytest tests/test_storage.py tests/test_locales.py -v` → FAIL.
- [ ] **Step 3:** Plugin'i yaz.
- [ ] **Step 4:** Run aynı komut → PASS.
- [ ] **Step 5: Commit.** `feat: storage-sqlite plugin`

---

### Task 3: `auth-local`

**Files:** `auth-local/{plugin.toml,__init__.py,locales/*}`, `tests/test_auth.py`

**Interfaces:**
- Produces: `setup(ctx) -> LocalAuth`.
  - `current_user() -> {"id": "local", "name": <ctx.t("user.name")>, "roles": ["admin"]}`. İsim çağrı anında çevrilir.
  - `has(permission) -> True` her durumda.
  - `plugin.toml` içinde `provides = "auth"` bulunur. `requires` yoktur.
- locales: `"user.name"` (tr `"Yönetici"`, en `"Administrator"`).

- [ ] **Step 1: Failing tests**
```python
def test_local_user_and_permissions(home):
    k = make_kernel(home, ["storage-sqlite", "auth-local"], {"storage": "storage-sqlite", "auth": "auth-local"})
    r = load(k)
    assert r.broken == {} and {"storage-sqlite", "auth-local"} <= set(r.loaded)
    auth = k.roles["auth"]
    assert auth.current_user()["id"] == "local" and auth.current_user()["roles"] == ["admin"]
    assert auth.has("anything") is True
def test_storage_uses_auth_user(home, monkeypatch):
    k = make_kernel(...)                                   # aynı
    load(k); monkeypatch.setattr(sys.modules["ngui_plugins.storage_sqlite"], "in_request", lambda: True)
    k.roles["storage"].for_plugin("p").set("k", 1)
    assert k.roles["storage"].for_plugin("p").for_user("local").get("k") == 1
```
- [ ] **Step 2:** Run `.venv/bin/pytest tests/test_auth.py tests/test_locales.py -v` → FAIL.
- [ ] **Step 3:** Plugin'i yaz.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit.** `feat: auth-local plugin`

---

### Task 4: `theme-default`

**Files:** `theme-default/{plugin.toml,__init__.py,theme.css,locales/*}`, `tests/test_theme.py`

**Interfaces:**
- Produces: `setup(ctx) -> DefaultTheme`.
  - `setup` sırasında `ui.add_css(ctx.path / "theme.css", shared=True)` çağrılır. Bu, tüm sayfalarda geçerli olan token'ları yükler.
  - `mode` property'si o anki kullanıcının seçimini döndürür: `ctx.storage.get("mode", "auto")`. İstek dışında `"auto"` döner.
  - `set_mode(mode)`: `mode` değeri `{"light", "dark", "auto"}` dışındaysa `ValueError`. Değeri storage'a yazar ve o anki sayfaya `ui.dark_mode(value)` uygular. Değer eşlemesi: `light` → `False`, `dark` → `True`, `auto` → `None`. **Layout her sayfanın başında `theme.set_mode(theme.mode)` çağırır.** Bu çağrı, kullanıcının kayıtlı seçimini sayfaya uygular (sözleşmede metot bu, ayrı bir `apply` yok).
  - `card(title=None, actions=None)`: `ui.card().classes("ngui-card")` bağlam yöneticisi döndürür. `title` varsa üstte `ngui-card-title` sınıflı etiket olur, `actions` callable ise başlık satırının sağına çizilir.
  - `kpi(label, value, icon=None, tone="neutral")`: `ngui-kpi` kartı çizer. Etiket büyük harfle, küçük ve gri olur. Değer büyük ve ton renginde gösterilir. İkon sağ üstte, ton renginde durur. Bilinmeyen `tone` değeri `neutral` kabul edilir.
  - `page_header(title, description=None)`: büyük kalın başlık, bir satırlık gri açıklama ve altında ince ayırıcı (`ngui-page-header`).
- `theme.css` CSS değişkenlerini `:root` ve `body.body--dark` altında tanımlar: `--ngui-bg`, `--ngui-surface`, `--ngui-border`, `--ngui-text`, `--ngui-muted`, `--ngui-primary`, `--ngui-success`, `--ngui-warning`, `--ngui-danger`, `--ngui-neutral`, `--ngui-radius` (8px), `--ngui-gap` (12px).
  - Açık mod değerleri: bg `#f5f6f8`, surface `#ffffff`, border `#e5e7eb`, text `#111827`, muted `#6b7280`, primary `#1f2937`, success `#16a34a`, warning `#b45309`, danger `#dc2626`, neutral `#6b7280`.
  - Koyu mod değerleri: bg `#0f1115`, surface `#171a21`, border `#262a33`, text `#e5e7eb`, muted `#9ca3af`, primary `#e5e7eb`, success `#22c55e`, warning `#f59e0b`, danger `#f87171`, neutral `#9ca3af`.
  - Sınıflar: `.ngui-card` (surface, 1px border, radius, gölge yok), `.ngui-card-title`, `.ngui-kpi`, `.ngui-kpi-label`, `.ngui-kpi-value`, `.ngui-tone-<tone>` (renk) ve `.ngui-page-header`. Ayrıca `body` arka planı `var(--ngui-bg)` olur, Quasar `q-card` gölgesi kaldırılır.
- `setup`, Quasar marka renklerini de token'larla eşler. `ui.colors(primary=..., positive=..., warning=..., negative=...)` çağrısı sayfa bağlamı gerektiriyorsa bunu `set_mode` içinde yap. NiceGUI 4'te `ui.colors` için global bir yol varsa onu kullan ve raporda belirt.
- locales: `"mode.light"`, `"mode.dark"`, `"mode.auto"`. Tema bunları kendi düğme metinlerinde kullanmaz; layout'taki tema seçicisi kendi çevirilerini kullanır. Anahtarlar, `test_locales_complete_and_equal` testinin dosyaları boş bulmaması için vardır.

- [ ] **Step 1: Failing tests**
```python
def test_theme_loads_as_role(home):
    k = make_kernel(home, ["storage-sqlite", "auth-local", "theme-default"], {**{r: REAL_ROLES[r] for r in ("storage", "auth", "theme")}})
    r = load(k); assert "theme-default" in r.loaded and k.roles["theme"].mode == "auto"
def test_set_mode_validates(home):
    ...; with pytest.raises(ValueError): k.roles["theme"].set_mode("blue")
def test_css_tokens_light_and_dark():
    css = (REPO / "theme-default" / "theme.css").read_text()
    for var in ["--ngui-bg", "--ngui-surface", "--ngui-border", "--ngui-text", "--ngui-muted",
                "--ngui-primary", "--ngui-success", "--ngui-warning", "--ngui-danger", "--ngui-neutral"]:
        assert css.count(var + ":") >= 2, var        # :root + body.body--dark
    assert "body.body--dark" in css
```
  Arayüz davranışı (kpi, card, page_header ve dark mode) Task 7'deki uçtan uca testlerde ve görsel kontrolde doğrulanır.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Plugin'i yaz. **Step 4:** Run → PASS.
- [ ] **Step 5: Commit.** `feat: theme-default plugin`

---

### Task 5: `layout-sidebar`

**Files:** `layout-sidebar/{plugin.toml,__init__.py,locales/*}`, `tests/test_layout.py`

**Interfaces:**
- Consumes: `ctx.role("auth")`, `ctx.role("theme")` (çizim anında), `ctx.i18n.set_lang`, `ctx.i18n.current_lang()`, `ctx.i18n.languages()`, `ctx.storage` (menünün açık/kapalı durumu).
- Produces: `setup(ctx) -> SidebarLayout`.
  - `SLOTS = ("nav", "header", "main", "statusbar")`.
  - `page(path, title, icon=None, permission=None) -> decorator`. Kayıt `self.pages` listesine eklenir: `PageEntry(path, title, icon, permission)`, sıra kayıt sırasıdır. Kayıt sırasında `@ui.page(path)` ile bir sarmalayıcı tanımlanır. Sarmalayıcı `self.frame(entry)` içinde `fn()` çağırır. Dekoratör `fn`'i değiştirmeden döndürür.
  - `add(slot, builder)`: `slot` değeri `SLOTS` içinde değilse sessizce döner. Değilse builder `self.slots[slot]` listesine eklenir.
  - `title` bir callable ise her çizimde çağrılır (`_text(title)`).
  - `/` adresine bir ana sayfa kaydedilir. Başlığı `ctx.t("home.title")`, açıklaması `ctx.t("home.description")` olur, altında `main` yuvasındaki builder'lar duyarlı bir ızgarada çizilir. Hiç builder yoksa ve kayıtlı sayfa varsa bu sayfaların kart listesi gösterilir (her kart sayfa bağlantısıdır).
  - `frame(entry)` çiziminin sırası:
    1. `theme.set_mode(theme.mode)`.
    2. **Üst bar** (`ui.header`): solda uygulama adı `ctx.t("app.name")`. Sağda sırasıyla `header` yuvası, dil seçici (`TR / EN` düğmeleri; `languages()` listesinden büyük harfle, aktif olan vurgulu; tıklayınca `set_lang`), tema seçici (ikon düğmesi; light → dark → auto döngüsü; ikonlar `light_mode` / `dark_mode` / `brightness_auto`; tıklayınca `theme.set_mode(...)` ve `ui.navigate.reload()`) ve kullanıcı menüsü (`person` ikonu ile `current_user()["name"]`).
    3. **Sol menü** (`ui.left_drawer`): dar (mini) ikon rayı, varsayılan olarak kapalı (mini). Önce yetkili sayfaların ikonları gelir; ikonun yanında etiket yalnızca genişletilmiş modda görünür. Mini modda başlık tooltip olarak gösterilir. Aktif sayfa vurgulanır. Altta `nav` yuvası, ince bir ayırıcı ve en altta genişlet/daralt düğmesi (`chevron_right` / `chevron_left`) bulunur. Menü durumu `ctx.storage` içinde `"drawer.expanded"` anahtarıyla tutulur.
    4. **İçerik:** önce breadcrumb (`home` ikonu, `ctx.t("home.title")`, `›`, sayfa başlığı; ana sayfada yalnızca ilki), sonra sayfa içeriği.
    5. **Alt bar** (`ui.footer`): yalnızca `statusbar` yuvasında builder varsa çizilir.
  - Yetki kontrolü: `permission` doluysa ve `auth.has(permission)` False ise menüde gösterilmez, sayfada içerik yerine `ctx.t("forbidden")` metni yer alır. Bir yuva builder'ı ya da sayfa fonksiyonu hata fırlatırsa `ctx.log.exception` ile loglanır, o alanda `ctx.t("error.render")` gösterilir, sayfanın geri kalanı çizilir.
  - Stil yalnızca `var(--ngui-*)` değişkenleri ve tema sınıflarıyla yapılır. Üst bar beyaz yüzeyli olur, altında 1px kenarlık bulunur. Menü yüzey renginde olur, sağında 1px kenarlık bulunur. İçerik dolgusu `var(--ngui-gap)`, sayfa genişliği tamdır.
- `plugin.toml`: `provides = "layout"`, `requires = []`. Auth ve theme rolleri layout'tan önce yüklenir ve çizim anında `ctx.role()` ile alınır.
- locales: `"app.name"` (tr ve en `"ngui"`), `"home.title"` (tr `"Ana sayfa"`, en `"Home"`), `"home.description"`, `"forbidden"`, `"error.render"`, `"menu.expand"`, `"menu.collapse"`, `"theme.toggle"`, `"lang.switch"`.

- [ ] **Step 1: Failing tests** (birim düzeyi; sayfa çizimi Task 7'de)
```python
def test_layout_loads_with_all_roles(home):
    k = make_kernel(home, ["storage-sqlite", "auth-local", "theme-default", "layout-sidebar"], REAL_ROLES)
    r = load(k); assert r.missing_roles == [] and r.broken == {}
def test_unknown_slot_is_ignored(loaded):
    loaded.roles["layout"].add("sidebar", lambda: None)
    assert "sidebar" not in loaded.roles["layout"].slots
def test_page_registers_entry_and_returns_fn(loaded):
    fn = lambda: None
    assert loaded.roles["layout"].page("/x", lambda: "X", icon="star", permission="p")(fn) is fn
    e = loaded.roles["layout"].pages[-1]; assert (e.path, e.icon, e.permission) == ("/x", "star", "p")
```
- [ ] **Step 2:** Run → FAIL. **Step 3:** Plugin'i yaz. **Step 4:** Run → PASS.
- [ ] **Step 5: Commit.** `feat: layout-sidebar plugin`

---

### Task 6: `store`

**Files:** `store/{plugin.toml,__init__.py,locales/*}`, `tests/test_store.py`

**Interfaces:**
- Consumes: `ctx.kernel.manager` (`status()`, `catalog()`, `add(name_or_url)`, `remove(id)`, `update(id)`, `rollback(id)`, `enable(id)`, `disable(id)`, `use(role, id)`, `sync_deps()`), `ctx.kernel.restart()`, `ctx.kernel.result.broken`, `ctx.role("storage").purge(id)`, `ctx.i18n.t("core", err.key, **err.vars)` (çekirdeğin hata metinleri), `ngui.NguiError`.
- Produces:
  - `setup(ctx)`: `/store` sayfasını kaydeder (`title=lambda: ctx.t("title")`, `icon="extension"`, `permission="store.manage"`). Dönüş değeri yoktur.
  - Saf mantık testlerde kullanılmak üzere fonksiyon olarak ayrılır: `run_action(manager, action: str, *args) -> tuple[str, dict] | None`. Başarıda `None` döner. `NguiError` yakalanırsa `(err.key, err.vars)` döner; çağıran taraf bunu `ctx.i18n.t("core", key, **vars)` ile çevirir. `action` değeri `{"add","remove","update","rollback","enable","disable","use"}` içinde olmalıdır. Başarılı her işlemden sonra `manager.sync_deps()` çağrılır; bu da `NguiError` fırlatabilir ve aynı şekilde yakalanır.
  - Sayfa yapısı (theme bileşenleriyle):
    1. `page_header(t("title"), t("description"))`.
    2. **Kurulu** kartı: `manager.status()` satırları tablo halinde gösterilir. Sütunlar: ad (manifest adı seçili dilde, yoksa id), kaynak, rol, kısa commit ve durum (sorun varsa `danger` tonlu metin). Her satırda işlem düğmeleri yer alır: aç/kapat, güncelle, geri al, kaldır, veriyi sil. Rol plugin'lerinde kaldır ve kapat düğmeleri yoktur. Core plugin'lerde kaldır ve güncelle yoktur; core güncellemesi kartın başlığındaki tek bir "Core'u güncelle" düğmesiyle (`update("core")`) yapılır.
    3. **Katalog** kartı: `manager.catalog()` sonucundaki her girdi için id, açıklama ve "Kur" düğmesi gösterilir. Kurulu olanlarda düğme pasif olur. Katalog boşsa `t("catalog.empty")` metni çıkar. Kartın altında URL ile kurma alanı ve düğmesi bulunur.
    4. **Roller** kartı: dört rol için o rolü sağlayabilen kurulu plugin'ler bir `ui.select` içinde listelenir; seçim değişince `use(role, id)` çağrılır.
  - İşlem akışı:
    1. Onay gerektiren işlemler (kaldır, veriyi sil, geri al, rol değiştir) önce `ui.dialog` ile onay ister.
    2. İşlem `await run.io_bound(run_action, manager, action, *args)` ile çalışır; bu sırada düğmeler pasif olur ve bir spinner görünür.
    3. Hata varsa `ui.notify(ctx.i18n.t("core", key, **vars), type="negative")` gösterilir ve yeniden başlatma yapılmaz.
    4. Başarılıysa `ui.notify(t("restarting"), type="positive")` gösterilir, ardından `ui.timer(0.8, ctx.kernel.restart, once=True)` çalışır. İstemci yeniden bağlanınca sayfa yenilenir.
    5. "Veriyi sil" işlemi `storage.purge(id)` çağırır, yeniden başlatma yapmaz, yalnızca bildirim gösterir.
- locales: `"title"` (tr `"Plugin Mağazası"`, en `"Plugin Store"`), `"description"`, `"installed"`, `"catalog"`, `"catalog.empty"`, `"roles"`, `"install"`, `"install.url"`, `"remove"`, `"update"`, `"update.core"`, `"rollback"`, `"enable"`, `"disable"`, `"purge"`, `"confirm"`, `"cancel"`, `"confirm.remove"`, `"confirm.purge"`, `"confirm.rollback"`, `"confirm.role"`, `"restarting"`, `"purged"`, `"col.name"`, `"col.source"`, `"col.role"`, `"col.commit"`, `"col.status"`, `"status.ok"`.

- [ ] **Step 1: Failing tests** (sahte manager ile saf mantık)
```python
class FakeManager:
    def __init__(self, fail=None): self.calls, self.fail = [], fail
    def __getattr__(self, name):
        def f(*a):
            self.calls.append((name, a))
            if self.fail == name: raise NguiError("err.git", detail="offline")
        return f
def test_run_action_success_syncs_deps():
    m = FakeManager(); assert run_action(m, "add", "notes") is None
    assert m.calls == [("add", ("notes",)), ("sync_deps", ())]
def test_run_action_error_returns_key_and_vars():
    assert run_action(FakeManager(fail="add"), "add", "x") == ("err.git", {"detail": "offline"})
def test_run_action_deps_error():
    assert run_action(FakeManager(fail="sync_deps"), "enable", "x")[0] == "err.git"
def test_run_action_rejects_unknown_action():
    with pytest.raises(ValueError): run_action(FakeManager(), "rm_rf", "/")
def test_store_registers_page(home):
    k = make_kernel(home, PLUGINS, REAL_ROLES); k.manager = Manager(home); r = load(k)
    assert "store" in r.loaded and any(e.path == "/store" for e in k.roles["layout"].pages)
```
- [ ] **Step 2:** Run → FAIL. **Step 3:** Plugin'i yaz. **Step 4:** Run → PASS.
- [ ] **Step 5: Commit.** `feat: plugin store`

---

### Task 7: Uçtan uca doğrulama

**Files:** `tests/test_e2e.py`; bulunan hatalar için ilgili plugin dosyaları.

**Interfaces:** Consumes `start_app`, `fetch`, ve tüm plugin'ler.

- [ ] **Step 1: E2E testleri**
```python
def test_home_renders_in_layout(app):            # app = start_app(home, PLUGINS, REAL_ROLES)
    html = fetch(app.url + "/")
    assert "Ana sayfa" in html and "ngui" in html
def test_store_page_renders(app):
    html = fetch(app.url + "/store"); assert "Plugin Mağazası" in html and "storage-sqlite" in html
def test_unknown_path_is_404_not_recovery(app):
    assert "Eksik rol" not in fetch(app.url + "/nope", ok_statuses=(404,))
def test_english_default_lang(home, tmp_path):   # config default_lang="en"
    ...; assert "Home" in fetch(url + "/") and "Plugin Store" in fetch(url + "/store")
def test_no_broken_plugins_logged(app):
    assert "setup failed" not in app.log() and "Traceback" not in app.log()
```
  (`fetch` için `ok_statuses` parametresini ekle. `app` fixture'ı `(proc, url, log)` döndüren küçük bir nesne olsun.)
- [ ] **Step 2:** Run `.venv/bin/pytest -q` → tümü PASS. Hata çıkarsa ilgili plugin'de düzelt.
- [ ] **Step 3: Görsel kontrol (kontrolcü yapar, implementer değil).** Uygulama `NGUI_PORT=8765` ile başlatılır ve tarayıcı panelinde `/`, `/store` açılır. Kontrol edilenler: referans ekranla tasarım dili (zemin, kartlar, ikon menü, üst bar), tema değişimi, dil değişimi ve menünün genişlemesi. Bulgular bir düzeltme turuna gider.
- [ ] **Step 4: Commit.** `test: end-to-end checks for core plugins`

---

## Bitiş

- [ ] İki repoda da `.venv/bin/pytest -q` → PASS.
- [ ] `wc -l */__init__.py` → plugin başına sınırlar içinde.
- [ ] **Push (kullanıcı onayıyla):** önce `n_gui` reposunda `git push`, sonra `nicegui-core-plugins` reposunda `git remote add origin https://github.com/ilkermansur/nicegui-core-plugins.git && git push -u origin main`.
- [ ] **Gerçek akış (push sonrası):** `n_gui` klasöründe `.env` içine `NGUI_CORE_REPO=https://github.com/ilkermansur/nicegui-core-plugins` ve `NGUI_HOST_PORT=18080` yazılır, ardından `docker compose up -d --build` çalıştırılır. `http://127.0.0.1:18080/` adresi ana sayfayı layout içinde göstermeli, `docker compose exec app ngui list` beş core plugin'i sorunsuz listelemeli.
