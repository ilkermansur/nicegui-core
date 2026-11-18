# ngui Plugin Sözleşmesi (sürüm 1.0)

Bu belge plugin yazarının okuması gereken tek belgedir. İskelet için: `ngui new <ad>`.

## 1. Klasör yapısı ve `plugin.toml`

```
nicegui-plugin-<id>/
  plugin.toml          # zorunlu
  __init__.py          # def setup(ctx): ...
  locales/tr.toml      # zorunlu
  locales/en.toml      # zorunlu
```

| Alan | Zorunlu | Anlam |
|---|---|---|
| `id` | evet | `^[a-z][a-z0-9-]*$`; `core` ve `core-plugins` ayrılmış; klasör/repo adındaki `<id>` ile aynı olmalı |
| `version` | evet | Sürüm metni |
| `name`, `description` | hayır | `{ tr = "...", en = "..." }` ya da düz metin (düz metin `en` sayılır) |
| `core` | hayır | Sözleşme sürümü aralığı, varsayılan `">=1,<2"`; uyumsuz plugin "bozuk" olur |
| `provides` | hayır | Rol dolduruyorsa `"storage"`, `"auth"`, `"theme"` veya `"layout"` |
| `requires` | hayır | Başka plugin id'leri; biri yoksa/bozuksa bu plugin yüklenmez; yükleme sırası buna göre |
| `dependencies` | hayır | pip bağımlılıkları (`["openai>=1.0"]`); NiceGUI ve çekirdeğin kendi paketlerini gölgeleyemez (onlar önce bulunur) |
| `permissions` | hayır | Tanımladığı yetki adları (`["notes.edit"]`) |

Bozuk `plugin.toml`, hata veren `setup` ya da eksik `requires` yalnızca o plugin'i atlatır; uygulama açılır.

## 2. `setup(ctx)` ve `ctx`

`setup(ctx)` açılışta bir kez çağrılır. Sayfa kodu ise istek geldiğinde çalışır.

| Üye | Anlam |
|---|---|
| `ctx.id`, `ctx.manifest`, `ctx.path` | Kimlik, okunmuş manifest, plugin klasörü (`Path`) |
| `ctx.log` | `logging.Logger` (`ngui.<id>`) |
| `ctx.role(name)` | Rol nesnesi; yüklü değilse `LookupError`. Yalnızca önceden yüklenen roller görülür |
| `ctx.storage` | Kısayol: `ctx.role("storage").for_plugin(ctx.id)` |
| `ctx.bus` | Olay yolu (bkz. 4) |
| `ctx.services` | Servis kaydı (bkz. 4) |
| `ctx.t(key, **vars)` | Çeviri (bkz. 5) |
| `ctx.i18n` | Çeviri nesnesi; `ctx.i18n.set_lang("en")` dili değiştirir (genelde yalnızca layout kullanır) |

Yükleme sırası: `storage`, `auth`, `theme`, `layout`, sonra özellik plugin'leri. Sayfaları her zaman `layout.page` ile kaydedin.

## 3. Roller

Her rolü tam bir plugin doldurur. Özellik plugin'i hangi plugin'in doldurduğunu bilmez, yalnızca `ctx.role("<ad>")` kullanır.

| Rol | Üye | Anlam |
|---|---|---|
| `storage` | `for_plugin(plugin_id)` -> store | Plugin'e ait anahtar-değer alanı |
| | `purge(plugin_id)` | Plugin'in tüm verisini siler |
| store | `get(key, default=None)`, `set(key, value)`, `delete(key)`, `list(prefix="")` | JSON değerler |
| | `shared` | Aynı plugin'in tüm kullanıcıları için ortak kapsam |
| | `for_user(user_id)` | İstek dışından belirli kullanıcının verisi |
| `auth` | `current_user()` | `{id, name, roles}` |
| | `has(permission)` | `bool` |
| `theme` | `mode`, `set_mode(mode)` | `"light"`, `"dark"` veya `"auto"` |
| | `card(title=None, actions=None)` | Kart |
| | `kpi(label, value, icon=None, tone="neutral")` | KPI kartı |
| | `page_header(title, description=None)` | Sayfa başlığı |
| `layout` | `page(path, title, icon=None, permission=None)` | Sayfa kaydeden dekoratör; menüye ekler, yetkiyi auth'a sorar |
| | `add(slot, builder)` | Yuvaya (`nav`, `header`, `main`, `statusbar`) UI ekler; bilinmeyen yuva sessizce yok sayılır |

```python
def setup(ctx):
    @ctx.role("layout").page("/notes", ctx.t("title"), icon="notes", permission="notes.edit")
    def page():
        ctx.role("theme").page_header(ctx.t("title"), ctx.t("description"))
        ctx.role("theme").kpi(ctx.t("total"), len(ctx.storage.list()), tone="success")
```

**Rol plugin'i yazıyorsanız:** `plugin.toml`'da `provides` yazın ve `setup(ctx)` rolün uygulamasını **döndürsün** (`return MyTheme()`). `None` dönerse plugin "bozuk" olur. Plugin yalnızca config'te o role atanmışsa (`ngui use <rol> <id>`) yüklenir; atanmamışsa sessizce atlanır. Özellik plugin'inin dönüş değeri yok sayılır. Roller özellik plugin'lerinden önce yüklendiği için bir rol plugin'inin `requires` listesi yalnızca kendinden önce yüklenen plugin'leri içerebilir; aksi halde "missing requirement" ile bozuk olur.

**Depolama kuralları:**
- Varsayılan kapsam `(plugin, o anki kullanıcı)`; kullanıcı her çağrıda `auth.current_user()` ile sorulur, `setup` sırasında sabitlenmez.
- İstek bağlamı dışında (zamanlayıcı, bus dinleyicisi, `setup`) `ctx.storage` hata verir; orada `.shared` ya da `.for_user(id)` kullanın.
- Plugin kaldırılınca verisi silinmez, yeniden kurulunca geri gelir; yalnızca açık bir `purge` siler.
- Plugin'ler arası ortak alan yoktur; paylaşım bus ile yapılır.
- Kullanıcı ve yetki varsayımı yapmayın: kullanıcıyı `auth.current_user()`, yetkiyi `auth.has()` ile sorun.

## 4. Bus ve servisler

| Çağrı | Davranış |
|---|---|
| `ctx.bus.on(olay, fn)` / `ctx.bus.off(olay, fn)` | Dinleyici ekler / çıkarır; `fn(data)`, `async` olabilir |
| `ctx.bus.emit("notes.created", data)` | Ateşle ve unut; bir dinleyicinin hatası diğerlerini engellemez, `emit` hata fırlatmaz |
| `ctx.services.provide("notes.api", obj)` | Servis sunar (aynı ad tekrar verilirse uyarı + üzerine yazar) |
| `ctx.services.get("notes.api")` | Nesne ya da `None` |

**Başka bir plugin'i asla import etmeyin.** İhtiyaç varsa: `requires` içine yazın (yoksa siz de yüklenmezsiniz) ya da servisi isteğe bağlı kullanın (`None` ise özelliği gizleyin). Olay ve servis adlarını `<id>.` ile başlatın.

## 5. Dil (TR / EN)

- `locales/tr.toml` ve `locales/en.toml` zorunlu; düz anahtar-değer: `"kpi.total" = "Toplam: {count}"`.
- Arayüzde sabit metin yok; her metin `ctx.t("kpi.total", count=5)` ile gelir. Anahtarlar plugin'e özeldir.
- Geri düşme: seçili dil, sonra `en`, sonra anahtarın kendisi. Eksik çeviri uygulamayı bozmaz.
- `ctx.t` o anki dili okur: sayfa fonksiyonunun içinde çağırın, `setup` içinde sabitlemeyin (yalnızca `layout.page` başlığı gibi kayıt anında gereken yerler hariç).
- Noktalı anahtarlar tırnak içinde yazılmalı: `"kpi.total" = "..."`. Tırnaksız `kpi.total = ...` iç içe tabloya dönüşür ve anahtar bulunmaz.
- Yeni dil için `locales/<dil>.toml` eklemek yeterlidir.

## 6. Tasarım

- Sabit renk kodu (hex, `rgb()`) yazmayın. Renk gerekiyorsa ton adı: `tone` değerleri `primary`, `success`, `warning`, `danger`, `neutral`.
- Renk, yazı tipi ve boşluk için tema CSS değişkenlerini kullanın: `--ngui-bg`, `--ngui-surface`, `--ngui-border`, `--ngui-text`, `--ngui-muted`, `--ngui-success` (diğer tonlar aynı kalıpta) ve Quasar marka renkleri.
- Açık/koyu mod temanın işidir; plugin buna karışmaz. Ortak parçalar için `theme.card/kpi/page_header`, gerisi düz NiceGUI.

## 7. Gateway plugin örüntüsü

Dış servise (Postgres, API) bağlanan plugin sıradan bir özellik plugin'idir:
- Adresi kendi ayarından ya da ortam değişkeninden okur (compose servis adı: `postgres:5432`, `http://api:8000`).
- Bağlantıyı servis olarak açar: `ctx.services.provide("db", client)`. Kullanan plugin `ctx.services.get("db")` ister, gateway'i import etmez.
- README'sine bağlandığı servisin örnek `docker-compose` bloğunu koyar.

## 8. Geliştirme döngüsü

```
ngui new notes --dir ~/code      # nicegui-plugin-notes/ iskeleti + ilk commit
ngui link notes ~/code/nicegui-plugin-notes   # klasörden doğrudan çalışır
# düzenle, sonra uygulamayı yeniden başlat
git push                         # bitince
ngui unlink notes
ngui update notes                # repo sürümüne dön
```

Uygulama her zaman lock dosyasındaki commit ile açılır; otomatik güncelleme yoktur.
