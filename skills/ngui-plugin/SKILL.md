---
name: ngui-plugin
description: Use when the user wants a new plugin, page, feature, theme, layout or service connection for their plugin-based NiceGUI tool "ngui" (repos nicegui-core, nicegui-core-plugins, nicegui-plugin-*), or says something like "plugin tabanlı nicegui aracım var, şu işe yarayacak bir plugin istiyorum". Also use when changing or reviewing an existing ngui plugin.
---

# ngui plugin geliştirme

ngui, NiceGUI üzerinde çalışan, plugin tabanlı bir araçtır. Çekirdek (`nicegui-core`, Python paketi `ngui`) **mühürlüdür**: kendi başına ekran çizmez, yalnızca plugin bulur, sıralar, yükler, kurar, kaldırır. Her özellik ayrı bir git reposunda (`nicegui-plugin-<id>`) yaşayan bir plugin'dir. Kullanıcının temel kuralı: **bir şey bozulursa en kötü ihtimalle o plugin'in başına dönülür, asla projenin başına.** Bu skill'deki her kural bunu korumak için var.

Repolar:
- `https://github.com/ilkermansur/nicegui-core`: çekirdek, `CONTRACT.md` (bağlayıcı sözleşme), Docker dosyaları
- `https://github.com/ilkermansur/nicegui-core-plugins`: `storage-sqlite`, `auth-local`, `theme-default`, `layout-sidebar`, `store`
- `https://github.com/ilkermansur/nicegui-plugin-api`: örnek özellik plugin'i (form, tablo, kullanıcıya özel veri, async HTTP)
- `https://github.com/ilkermansur/nicegui-plugin-dashboard`: örnek özellik plugin'i (veritabanı, grafik, diyalog, ortak veri, `ctx.data_dir`)

Yerelde genelde yan yana dururlar: `~/Desktop/n_gui`, `~/Desktop/nicegui-core-plugins`, `~/Desktop/nicegui-plugin-*`.

## 1. Başlamadan önce

1. `CONTRACT.md` dosyasını oku (yerelde `n_gui/CONTRACT.md`, yoksa GitHub'dan). Bu skill ile çelişirse sözleşme kazanır. Sözleşme sürümü `ngui/__init__.py` içindeki `CONTRACT_VERSION`'dır (bu skill yazılırken `1.1`).
2. İşe en çok benzeyen örnek plugin'i oku ve onun düzenini kopyala: form/tablo/HTTP ise `nicegui-plugin-api`, veritabanı/grafik/diyalog ise `nicegui-plugin-dashboard`.
3. Kullanıcıya en fazla şunları sor, gerisini kendin karar verip söyle: plugin'in kimliği (`id`), veriyi kimin göreceği (yalnızca kullanıcı mı, herkes mi), yetki gerekip gerekmediği, dış bir servise bağlanıp bağlanmadığı.

## 2. Ne tür bir plugin?

| İş | Tür | Ne demek |
|---|---|---|
| Yeni sayfa, ekran, araç (not, rapor, form, API ekranı) | **Özellik plugin'i** | `provides` yok. `setup(ctx)` sayfaları kaydeder, dönüş değeri yok sayılır |
| Postgres, Redis, bir REST servisi gibi dış servise bağlanmak ve bağlantıyı başka plugin'lere açmak | **Gateway plugin'i** | Özellik plugin'idir. Bağlantıyı `ctx.services.provide("<id>.client", obj)` ile sunar. Servisin kendisi ayrı bir Docker konteyneridir; kullanıcı onu `docker-compose.yml` dosyasına kendisi ekler |
| Tema, menü/yerleşim, depolama, kimlik doğrulamanın yerine geçmek | **Rol plugin'i** | `provides = "theme"` (ya da `layout`, `storage`, `auth`). `setup(ctx)` rolün uygulamasını **döndürür**. `ngui use <rol> <id>` ile atanmadıkça yüklenmez |
| Mevcut bir core plugin'in hatası (menü, tema, mağaza) | **Core plugin düzeltmesi** | `nicegui-core-plugins` reposunda, ilgili klasörde düzeltilir. Çekirdek değişmez |
| Sözleşmenin vermediği bir yetenek (örneğin `ctx`'te olmayan bir şey) | **Çekirdek eklemesi** | Dur ve kullanıcıya söyle. Aşağıdaki "Çekirdeğe dokunmak" bölümüne bak |

Bir plugin'i ikiye bölme (lego parçası kırılmaz). Bir özellik bütün olarak tek plugin'dir; ancak başka plugin'lerin de kullanacağı ortak bir yetenek (gateway gibi) ayrı plugin olur.

## 3. Repo yapısı

İskeleti her zaman çekirdeğin komutuyla oluştur, elle kurma:

```bash
ngui new <id> --dir ~/Desktop      # nicegui-plugin-<id>/ + git init + ilk commit
```

Hedef yapı:

```
nicegui-plugin-<id>/
  plugin.toml              zorunlu: kimlik ve bildirimler
  __init__.py              zorunlu: def setup(ctx); yalnızca arayüz
  logic.py | db.py         arayüzden bağımsız mantık (NiceGUI import etmez); test edilir
  locales/tr.toml          zorunlu
  locales/en.toml          zorunlu
  README.md                ne yapar, kurulum, ekran, yetki/güvenlik, nasıl çalışır, geliştirme
  pyproject.toml           pytest ayarı (templates/pyproject.toml)
  tests/harness.py         test düzeneği (templates/harness.py, olduğu gibi)
  tests/conftest.py        tek satır (templates/conftest.py)
  tests/test_locales.py    dil dosyası kontrolü (templates/test_locales.py)
  tests/test_logic.py      saf mantık testleri
  tests/test_page.py       uygulamayı gerçekten açan test
  .github/workflows/test.yml   CI (templates/test.yml)
  .gitignore               __pycache__/  .env  .venv/
```

Bu skill'in `templates/` klasöründeki dosyaları kopyala: `harness.py`, `conftest.py`, `test_locales.py` → `tests/`; `pyproject.toml` → kök; `test.yml` → `.github/workflows/` (bağımlılık satırını düzenle); `gitignore` → kökte `.gitignore`.

## 4. `plugin.toml`

```toml
id = "notes"                 # ^[a-z][a-z0-9-]*$ ; "core" ve "core-plugins" yasak; repo adı nicegui-plugin-<id>
version = "0.1.0"
core = ">=1,<2"              # ctx.data_dir kullanıyorsa ">=1.1,<2"
dependencies = ["httpx>=0.27"]   # yalnızca gerekiyorsa; pip adları
permissions = ["notes.edit"]     # tanımladığı yetkiler, <id>. ile başlar
# requires = ["db-gw"]       # bu plugin olmadan çalışamıyorsa; yoksa yazma
# provides = "theme"         # yalnızca rol plugin'i

[name]
tr = "Notlar"
en = "Notes"

[description]
tr = "Kullanıcıya özel notlar."
en = "Personal notes."
```

- `dependencies` uygulama açılırken `/data/pydeps` içine kurulur. NiceGUI'yi ve çekirdeğin kendi paketlerini (nicegui, tomli-w, packaging) ekleme; onları gölgeleyemezsin.
- `requires` yalnızca zorunlu bağımlılık içindir. Opsiyonel bir servis için `requires` yazma, `ctx.services.get(...)` ile `None` kontrolü yap.

## 5. `setup(ctx)` ve `ctx`

`setup(ctx)` açılışta **bir kez** çalışır. Sayfa fonksiyonu ise her istekte çalışır.

| Üye | Kullanım |
|---|---|
| `ctx.id`, `ctx.path`, `ctx.manifest`, `ctx.log` | Kimlik, plugin klasörü, okunmuş manifest, `logging.Logger` |
| `ctx.role("layout" \| "theme" \| "auth" \| "storage")` | Rol nesnesi. Yalnızca roller ve `requires` içindekiler senden önce yüklenir |
| `ctx.storage` | `(bu plugin, o anki kullanıcı)` kapsamında anahtar-değer. `get(key, default)`, `set(key, value)`, `delete(key)`, `list(prefix)`. Değerler JSON olmalı |
| `ctx.storage.shared` | Bu plugin'in bütün kullanıcıları için ortak alan. İstek dışında da çalışır |
| `ctx.storage.for_user(user_id)` | Belirli bir kullanıcının verisi; istek dışından |
| `ctx.data_dir` | Plugin'e ait dosya klasörü (`Path`); SQLite dosyası, yüklenen dosyalar. Sözleşme 1.1 ile geldi |
| `ctx.t(key, **vars)` | Çeviri. **Sayfa fonksiyonunun içinde** çağrılır, `setup` içinde sabitlenmez |
| `ctx.bus.on/off/emit` | Olaylar. Ad `<id>.` ile başlar: `notes.created` |
| `ctx.services.provide/get` | Servis kaydı. Ad `<id>.` ile başlar |
| `ctx.kernel` | **Kullanma.** Yalnızca sistem plugin'i `store` içindir |

Sayfa kaydı:

```python
from nicegui import ui

def setup(ctx):
    t = ctx.t

    @ctx.role("layout").page("/notes", lambda: t("title"), icon="sticky_note_2", permission="notes.edit")
    def page():                       # async def de olabilir
        theme = ctx.role("theme")
        theme.page_header(t("title"), t("description"))
        ...
```

- Sayfayı **her zaman** `layout.page` ile kaydet; `ui.page` kullanma. Menü, breadcrumb, ana sayfa kartı, yetki kontrolü ve hata yakalama layout'tan gelir.
- Başlığı `lambda: t("title")` olarak ver; dil değişince menü güncellenir.
- Sayfa yolu `/<id>` ya da `/<id>/...` olur; başka plugin'in yolunu kullanma, `/` yoluna sayfa koyma.
- Yuvalar: `layout.add("header" | "nav" | "main" | "statusbar", builder)`. `main` yuvası ana sayfaya kart ekler.
- Tema yardımcıları: `theme.page_header(title, description)`, `theme.card(title=None, actions=callable)`, `theme.kpi(label, value, icon=None, tone="neutral")`; tonlar `primary`, `success`, `warning`, `danger`, `neutral`.
- Yetki: `ctx.role("auth").has("notes.edit")`. Kullanıcı: `ctx.role("auth").current_user()` → `{id, name, roles}`. Kullanıcı ve yetki için asla varsayım yapma.

## 6. Kesin kurallar

1. **Başka plugin'i import etme.** İhtiyaç varsa `requires` + `ctx.services.get(...)`, ya da bus olayları.
2. **Ekranda sabit metin yok.** Her metin `ctx.t(...)` ile gelir. `locales/tr.toml` ve `locales/en.toml` aynı anahtarlara sahip olur. Noktalı anahtarlar tırnak içinde: `"err.url" = "..."`.
3. **Renk kodu yok** (hex, `rgb()`). Renk için ton adları, Quasar marka renkleri (`primary`, `positive`, `warning`, `negative`) ve tema değişkenleri (`--ngui-bg`, `--ngui-surface`, `--ngui-border`, `--ngui-text`, `--ngui-muted`, `--ngui-primary`, `--ngui-success`, `--ngui-warning`, `--ngui-danger`, `--ngui-radius`, `--ngui-gap`). Açık/koyu mod temanın işidir.
4. **CSS sınıfları `ngui-<id>-` ile başlar** ve `ui.add_css(CSS, shared=True)` ile `setup` içinde bir kez eklenir. `.q-btn` gibi genel seçicileri stillendirme; bu bütün uygulamayı bozar.
5. **Olay döngüsünü bloklama.** Ağ: `httpx.AsyncClient` ile `await`. Veritabanı ya da ağır iş: `await run.io_bound(fn, ...)`. `time.sleep` yasak. Uzun işler sayfayı önce çizip veriyi `ui.timer(0.01, fill, once=True)` ile sonradan doldurur.
6. **`run.io_bound` iş parçacığında ve istek dışında (`setup`, timer, bus dinleyicisi) `ctx.storage` hata verir.** Orada `ctx.storage.shared` ya da `.for_user(id)` kullan; ya da veriyi okuyup thread'e parametre olarak ver.
7. **Hatalar dil anahtarıyla taşınır.** Mantık katmanı `class XError(Exception): key, vars` fırlatır, sayfa `ui.notify(t(e.key, **e.vars), type="negative")` gösterir. Bir plugin hatası uygulamayı düşürmez; yakalanmayan hata layout tarafından "hata" etiketiyle gösterilir, ama beklenen hataları kendin yakala.
8. **Güvenlik:** Sunucudan dış istek atan ya da veriyi değiştiren sayfa bir yetkiye bağlanır. SQL kullanıcı girdisiyle metin olarak kurulmaz; tablo ve sütun adları şemayla doğrulanır, sorgu SQLAlchemy ifadeleriyle kurulur. Parola ve token kod, repo ya da log içine girmez; ortam değişkeninden okunur.
9. **Kod sade kalır.** Arayüz `__init__.py`'de, mantık ayrı dosyada. Form durumu tek sözlük + `bind_value`. Yeniden çizilecek alan `@ui.refreshable`.

## 7. Test

Test düzeneği hazırdır; kopyala, değiştirme:
- `tests/harness.py`: `start_app(env=None) -> url` gerçek uygulamayı (`python -m ngui run`) core plugin'ler ve bu plugin bağlı olarak açar. `fetch(url)` sayfa gövdesini döner (NiceGUI ögeleri JSON olarak gövdenin içindedir, metin araması çalışır). `import_plugin_module("logic")` plugin modülünü paket olarak içe aktarır. `start_app.log()` uygulama logu.
- `pyproject.toml`: depo kökü plugin paketinin kendisi olduğu için pytest köke `--rootdir=tests --confcutdir=tests` ile sokulmaz. Bunu değiştirme.

En az şu testler olur:
- `test_locales.py`: TR ve EN aynı anahtarlar; kodda kullanılan her `t("...")` anahtarı mevcut.
- `test_logic.py`: mantık katmanının doğru ve hatalı girdileri; dış servis gerekiyorsa testte yerel bir `http.server` ya da geçici SQLite kullan, internete çıkma.
- `test_page.py`: `fetch(start_app() + "/<id>")` içinde `ngui-topbar` (layout içinde açıldı), sayfa başlığı ve temel etiketler var; logda `not loaded` ve `Traceback` yok.

Çalıştırma (repolar yan yanayken):

```bash
python3 -m venv .venv
.venv/bin/pip install -e ../n_gui[dev] pytest-asyncio <plugin bağımlılıkları>
.venv/bin/pytest -q
```

Core plugin'ler başka yerdeyse `NGUI_CORE_PLUGINS=/yol`.

## 8. Geliştirme ve yayın döngüsü

```bash
ngui link <id> ~/Desktop/nicegui-plugin-<id>   # çalışan uygulamada klasörden çalıştır
# düzenle → uygulama yeniden başlar (her ngui komutu bunu tetikler)
git push                                       # GitHub'da nicegui-plugin-<id> reposu (kullanıcı açar)
ngui unlink <id>
ngui add https://github.com/<kullanici>/nicegui-plugin-<id>    # ilk kurulum
ngui update <id>          # sonraki sürümler; ngui rollback <id> bir önceki commit'e döner
```

Docker içinde her komut `docker compose exec app ngui ...` biçimindedir. Uygulama her zaman kilit dosyasındaki commit'le açılır; otomatik güncelleme yoktur. Plugin yüklenmezse nedeni `docker compose logs app` içinde `plugin <id> not loaded: ...` satırında ve mağaza ekranındadır.

Push, GitHub reposu açmak ve token gibi işler kullanıcınındır: sor, kendin yapma.

## 9. Çekirdeğe dokunmak

Çekirdek mühürlüdür. Bir plugin için çekirdek **değiştirilmez**. Sözleşmenin vermediği bir şeye gerçekten ihtiyaç varsa:
1. Önce plugin içinde çözülüp çözülemeyeceğine bak (servis, bus, `shared`, `data_dir`).
2. Çözülemiyorsa dur; kullanıcıya eksik olanı, neden gerektiğini ve geriye uyumlu bir 1.x eklemesi önerisini söyle (yeni alan eklenir, var olan değişmez; `CONTRACT_VERSION` küçük sürüm artar; `CONTRACT.md` güncellenir; `scripts/acceptance.sh` çalışır).
3. Kullanıcı onaylamadan çekirdekte tek satır değiştirme.

Menü, tema, mağaza, depolama ya da kimlik davranışındaki hatalar çekirdekte değil, `nicegui-core-plugins` içindeki ilgili plugin'de düzeltilir.

## 10. Teslim kontrol listesi

- [ ] İskelet `ngui new` ile oluşturuldu; repo adı `nicegui-plugin-<id>`
- [ ] `plugin.toml`: id, sürüm, TR/EN ad ve açıklama, doğru `core` aralığı, gereken `dependencies` ve `permissions`
- [ ] Sayfalar `layout.page` ile, başlıklar `lambda: t(...)` ile; yollar `/<id>` altında
- [ ] Ekranda sabit metin yok; TR/EN anahtarları eşit
- [ ] Renk kodu yok; CSS sınıfları `ngui-<id>-` önekli
- [ ] Başka plugin import edilmedi; olay ve servis adları `<id>.` önekli
- [ ] Ağ/DB çağrıları `await` ya da `run.io_bound`; `ctx.storage` thread içinde kullanılmadı
- [ ] Veri kapsamı bilinçli seçildi: kullanıcıya özel `ctx.storage`, ortak `ctx.storage.shared`, dosya `ctx.data_dir`
- [ ] Değiştiren ya da dışarı istek atan işler bir yetkiye bağlı
- [ ] Mantık ayrı dosyada ve testli; `test_locales`, `test_logic`, `test_page` geçiyor
- [ ] CI dosyası, `.gitignore`, README (ne yapar, kurulum, ekran, yetki/güvenlik, nasıl çalışır, geliştirme)
- [ ] Çekirdek ve core plugin'ler değişmedi (değiştiyse kullanıcı onayı var)
- [ ] Tarayıcıda açık ve koyu modda bakıldı
