# NiceGUI Plugin Platformu — Tasarım

Tarih: 2026-11-18 · Durum: onaylandı

## 1. Niyet ve neden

Her şey için kullanılabilen bir NiceGUI uygulaması. Uygulamanın kendine ait bir amacı yok; ne olacağını takılan plugin'ler belirler (bugün not defteri, yarın sunucu izleme, öbür gün LLM sohbeti).

Neden: Çekirdeği bir kez yazıp kapatmak. Sonrasında her yeni fikir "yeni bir plugin projesi aç, yaz, tak" seviyesinde kalsın; beğenilmezse sökülsün. Çekirdek hiçbir zaman bir özellik yüzünden değişmesin.

**Lego benzetmesi (temel kural):** Parçalar takılır ve sökülür, ama bir parça hiçbir zaman kırılıp ikiye bölünmez ve başka bir parçanın içine el atılmaz. Bir şey istenirse ya yeni bir parça yazılır ya da var olanlar birbirine bağlanır.

## 2. Hedefler, hedef olmayanlar, anti-hedefler

**Hedefler**
- Çekirdek küçük, okunabilir ve "bitmiş" olsun. Hedef birkaç yüz satır.
- Core'un kendisi de plugin'lerden oluşsun. Layout, storage ve auth değiştirilebilir parçalar olsun.
- Bir plugin'i takmak ve sökmek tek komut ya da tek tık olsun. Söküm iz bırakmasın (veri hariç, bkz. §9).
- Uygulama bugün tek kullanıcılı çalışsın, ama sözleşme baştan çok kullanıcıya açık olsun.
- Yeni bir plugin, yalnızca sözleşme dokümanı (`CONTRACT.md`) okunarak yazılabilsin.
- Arayüz baştan iki dilli olsun: Türkçe (varsayılan) ve İngilizce.

**Hedef olmayanlar**
- Uygulama çalışırken yeniden başlatmadan plugin takıp sökmek. Her kur/kaldır/güncelle/aç/kapat işlemi uygulamayı yeniden başlatır.
- Plugin'leri birbirinden yalıtmak (sandbox). Plugin'ler aynı süreçte, tam güvenle çalışır.
- pip paketi olarak dağıtım.
- Bugün giriş ekranı ya da gerçek kullanıcı yönetimi.
- Uygulamanın Docker container'ı başlatması ya da yönetmesi. Servis container'larını kullanıcı `docker-compose.yml` dosyasına kendisi ekler.

**Anti-hedefler (teknik olarak çalışsa bile başarısızlık sayılır)**
- Çekirdeğin bir özellik için değiştirilmek zorunda kalması.
- Bir plugin'in başka bir plugin'in kodunu import etmesi.
- Bozuk bir plugin'in bütün uygulamayı açılmaz hale getirmesi.
- Kodun "esneklik" adına uzayıp karmaşıklaşması. Temel ilke: **kısa ve basit kod.**

## 3. Yaklaşımlar

Değerlendirilen yollar:

- **A) Klasör tabanlı, kendi küçük yükleyicimiz.** Her plugin bir klasör, içinde `plugin.toml` ve `setup(ctx)` var. En kısa ve en görünür yol.
- **B) Her plugin bir pip paketi (entry points).** Sürüm ve bağımlılık yönetimini pip yapar, ama her plugin için paketleme töreni gerekir. Kaldırınca bağımlılıklar ortamda kalır. Basitlik kaybolur.
- **C) A + `pluggy`.** Hazır hook sistemi getirir, ama roller, yuvalar ve auth yine bizim yazmamız gerekir. Kazancından çok soyutlama maliyeti var.

**Seçilen: A, git tabanlı dağıtımla.** Plugin'ler kullanıcının gözü önündeki bir klasörde değil, git repolarında yaşar. Uygulama bunları gizli bir yere çeker, pip'in `site-packages`'ı gibi. Nedeni: Elle kurcalanan klasörler bozuluyor. Değişiklik ise her zaman repo üzerinden (pull, düzenle, push, uygulamada "Güncelle") yapılmalı.

Repo düzeni için değerlendirilenler: tek monorepo, iki monorepo, ayrı repolar. **Seçilen:** Core plugin'ler tek repoda, diğer her plugin kendi reposunda (bkz. §5).

## 4. Mimari genel bakış

```
┌──────────────────────── bu proje (çekirdek) ────────────────────────┐
│  loader · roller/sözleşmeler · bus · plugin yöneticisi · CLI (ngui) │
└──────────────────────────────────────────────────────────────────────┘
          ▲ setup(ctx)                         ▲ setup(ctx)
┌─────────┴── nicegui-core-plugins ──┐   ┌─────┴── nicegui-plugin-<ad> ──┐
│ layout-sidebar  (rol: layout)      │   │ ai, notes, ... (özellik)       │
│ storage-sqlite  (rol: storage)     │   │                                │
│ auth-local      (rol: auth)        │   │                                │
│ theme-default   (rol: theme)       │   │                                │
│ store           (özellik)          │   │                                │
└────────────────────────────────────┘   └────────────────────────────────┘
```

**Çekirdek (bu proje), plugin olmayan tek parça:**
- **loader:** Etkin plugin'leri bulur, bağımlılık sırasına dizer, import eder ve `setup(ctx)` çağırır.
- **roller/sözleşmeler:** Rollerin arayüzlerini (Python `Protocol`) tanımlar.
- **bus:** Olaylar ve servisler. Lego'nun "tırtıkları" bunlar. Bir standart oldukları için plugin değil, çekirdeğin parçası.
- **plugin yöneticisi:** Kur, kaldır, güncelle, geri al, aç/kapat, link işlemleri ve yeniden başlatma. Hem CLI hem store plugin'i bu kütüphaneyi kullanır.
- **CLI `ngui`:** Uygulama açılmasa bile her şeyi düzeltebilmek için kurtarma yolu.

### 4.1 Roller

Rol, çekirdeğin tanımladığı bir sözleşmedir. **Her rolü aynı anda tam olarak bir plugin doldurur.** Özellik plugin'leri rolleri sadece `ctx.role("<ad>")` ile kullanır ve hangi plugin'in o rolü doldurduğunu bilmez.

| Rol | Ne sağlar | Varsayılan plugin |
|---|---|---|
| `layout` | Sayfa iskeleti ve adlandırılmış yuvalar: `nav`, `header`, `main`, `statusbar`. Plugin'ler sayfa kaydeder ve yuvalara içerik ekler. | `layout-sidebar` |
| `storage` | Plugin ve kullanıcı bazında ayrılmış veri ve ayar alanı. | `storage-sqlite` |
| `auth` | O anki kullanıcı, yetki kontrolü, (ileride) giriş sayfası. | `auth-local` (herkes "admin", giriş yok) |
| `theme` | Tasarım dili: renk, yazı tipi ve boşluk token'ları, açık/koyu mod, birkaç ortak UI parçası. | `theme-default` (bkz. §4.4) |

Sözleşmenin asgari yüzeyi (isimler builder'a bırakılabilir, anlam bağlayıcıdır):

- `layout.page(path, title, icon=None, permission=None)`: NiceGUI sayfası kaydeden dekoratör. İçeriği layout'un `main` yuvasına koyar, menüye ekler, yetkiyi auth'a sorar.
- `layout.add(slot, builder)`: Bir yuvaya UI parçası ekler. Bilinmeyen bir yuva verilirse sessizce yok sayılır. Böylece farklı yuvaları olan bir layout takıldığında plugin bozulmaz.
- `storage.for_plugin(plugin_id)` → `get/set/delete/list` (anahtar-değer, JSON).
  - Varsayılan kapsam `(plugin, o anki kullanıcı)`. Kullanıcı her çağrıda `auth.current_user()` ile sorulur, `setup()` sırasında sabitlenmez.
  - Bir istek bağlamı dışında çağrılırsa hata verir. İstek bağlamı dışı: zamanlayıcı, bus dinleyicisi, açılış kodu.
  - `.shared`: Aynı plugin'in **tüm kullanıcıları** için ortak kapsam. Plugin'ler arası ortak alan **yoktur**, plugin'ler arası paylaşım bus üzerinden yapılır.
  - `.for_user(user_id)`: İstek dışından belirli bir kullanıcının verisine erişmek için.
  - `storage.purge(plugin_id)`: Bir plugin'in tüm verisini siler. Store'daki "veriyi sil" işlemi bunu kullanır.
- `auth.current_user()` → `{id, name, roles}`; `auth.has(permission)` → `bool`.
- `theme.mode` (`"light" | "dark" | "auto"`), `theme.set_mode(mode)`. Seçim kullanıcı bazında storage'a yazılır.
- `theme.card(title=None, actions=None)`, `theme.kpi(label, value, icon=None, tone="neutral")`, `theme.page_header(title, description=None)`: Plugin'lerin tutarlı görünmesi için az sayıda ortak parça. Liste kasıtlı olarak kısa tutulur, geri kalan her şey düz NiceGUI ile yazılır.
- **Roller arası bağımlılık:** Önce storage yüklenir, sonra auth, sonra theme, sonra layout. Storage, auth'u yalnızca çağrı anında sorar, bu yüzden yükleme sırasında döngü oluşmaz. Auth plugin'i kendi kullanıcı kayıtlarını storage'ın `.shared` kapsamında tutabilir. *(builder kararı, onaylandı sayılmaz)*

Yeni bir rol eklemek çekirdeği değiştirmek demektir. Bu yüzden rol listesi kasıtlı olarak küçük tutulur. Rol olmayan her şey özellik plugin'idir.

### 4.2 Bus: plugin'ler arası iletişim

- **Olaylar:** `ctx.bus.on("notes.created", fn)`, `ctx.bus.emit("notes.created", data)`. Ateşle ve unut. Dinleyen yoksa bir şey olmaz.
- **Servisler:** `ctx.services.provide("ai.chat", obj)`, `ctx.services.get("ai.chat")` → nesneyi ya da `None` döndürür.
- **Kural:** Bir plugin başka bir plugin'i asla import etmez. Başka bir plugin'e ihtiyaç duyuyorsa iki yolu vardır:
  - `plugin.toml` içinde `requires` alanına yazar. Bu durumda o plugin yoksa kendisi yüklenmez.
  - Servisi isteğe bağlı kullanır, yani `None` gelirse o özelliği gizler.

### 4.3 `ctx` nesnesi

`setup(ctx)` fonksiyonuna verilir. İçinde şunlar bulunur: `ctx.id`, `ctx.manifest`, `ctx.role(name)`, `ctx.bus`, `ctx.services`, `ctx.storage` (kısayol: `ctx.role("storage").for_plugin(ctx.id)`), `ctx.t(key, **vars)` (bkz. §4.5), `ctx.log`, `ctx.path` (plugin'in kendi dosyaları, statik varlıklar için). Plugin'ler NiceGUI'yi doğrudan kullanabilir, ama sayfaları `layout.page` ile kaydetmeleri gerekir.

### 4.4 Tasarım dili

Hedef: Berrak, modern ve minimalist bir arayüz. Ekrana çok şey sığabilmeli, yani yoğunluk yüksek ama ferah. Referans, kullanıcının paylaştığı bir medikal cihaz kiralama panosunun ekran görüntüsü. Görsel: `docs/design/reference-dashboard.png`.

Referanstan alınan dil:
- **Zemin ve kartlar:** Açık gri bir zemin üzerinde beyaz kartlar. Kartların ince 1px kenarlığı ve hafif yuvarlak köşeleri var, gölge neredeyse yok. Kart başlıkları küçük ve kalın.
- **Kenar menüsü:** Solda dar, yalnızca ikonlardan oluşan bir menü. Altındaki `>` ile genişler ve etiketler görünür. Gruplar ince bir çizgiyle ayrılır.
- **Üst bar:** Solda logo ve uygulama adı. Sağda kullanıcı menüsü ve küçük kontroller (dil, tema anahtarı).
- **Sayfa başlığı:** Breadcrumb, büyük kalın başlık, bir satırlık gri açıklama, altında ince bir ayırıcı çizgi.
- **KPI kartları:** Büyük harfli küçük etiket, büyük sayı, sağ üstte anlamlı renkte küçük bir ikon.
- **Renkler:** Nötr gri tonlar üzerine az sayıda anlamlı ton kullanılır: `success` (yeşil), `warning` (amber), `danger` (kırmızı), `neutral` (gri), `primary`.
- **Tablolar:** Sade, çizgili ayırıcılar, büyük harfli olmayan başlıklar.

**Kurallar (değiştirilebilirliği garanti eden kısım):**
- Bütün renkler, yazı tipleri ve boşluklar `theme-default` plugin'inin tanımladığı **CSS değişkenleri** (`--ngui-bg`, `--ngui-surface`, `--ngui-border`, `--ngui-text`, `--ngui-muted`, `--ngui-success` …) ve Quasar marka renkleri üzerinden gelir. Bir plugin hiçbir zaman sabit bir renk kodu (hex) yazmaz. Bir renk gerektiğinde ton adını kullanır (`tone="warning"`).
- **Açık/koyu mod**, temanın kendisinin bir parçasıdır. NiceGUI'nin `dark_mode` özelliği ve token'ların koyu karşılıkları kullanılır. Anahtar üst bardadır, varsayılan değer `auto`'dur (sistem ayarını izler).
- Layout plugin'i de temanın token'larını kullanır. Böylece başka bir tema takıldığında layout da ona uyar.
- Beklentiyi karşılamayan bir tema, başka bir `theme-*` plugin'i takılarak (`ngui use theme theme-x`) bütünüyle değiştirilebilir. Hiçbir özellik plugin'ine dokunmak gerekmez.

### 4.5 Dil desteği (TR / EN)

Dil desteği bir rol değil, `plugin.toml` gibi çekirdeğin bir **standardıdır**. Bus gibi o da lego'nun tırtığıdır. Çekirdekteki kodu birkaç düzine satırdır.

- **Çeviri dosyaları:** Her plugin çevirilerini kendi klasöründe tutar: `locales/tr.toml` ve `locales/en.toml`. İçlerinde düz anahtar-değer çiftleri bulunur, örneğin `"kpi.total" = "Toplam cihaz"`.
- **Kullanım:** Plugin metinleri `ctx.t("kpi.total", count=5)` ile alır. Anahtarlar plugin'e özeldir, iki plugin'in anahtarları çakışmaz.
- **Dil seçimi:** O anki dil kullanıcı bazında tutulur. Çekirdek bunu storage rolünde kendi `core` alanına yazar. Seçim yapılmamışsa config'deki `default_lang` kullanılır, varsayılanı `"tr"`.
- **Geri düşme sırası:** Önce seçili dil, yoksa `en`, o da yoksa anahtarın kendisi gösterilir. Eksik bir çeviri uygulamayı bozmaz, sadece göze batar.
- **Dil anahtarı:** Üst barda `TR / EN` şeklinde durur, referans ekrandaki `DE` gibi. Layout bunu çekirdeğin `ctx.i18n.set_lang()` fonksiyonuyla kurar. Dil değişince sayfa yenilenir.
- **Plugin tanıtımı:** `plugin.toml` içindeki `name` ve `description` alanları da iki dillidir: `name = { tr = "Notlar", en = "Notes" }`. Store bunları seçili dilde gösterir.
- **Kural:** Bütün core plugin'ler (`layout-sidebar`, `storage-sqlite`, `auth-local`, `theme-default`, `store`) TR ve EN çevirileri eksiksiz olarak gelir. Arayüzde sabit yazılmış metin bulunmaz. Kurtarma sayfası da aynı mekanizmayı kullanır. CLI çıktısının dili `NGUI_LANG` ortam değişkenine göre belirlenir. *(builder kararı)* `ngui new` şablonu da iki dil dosyasıyla gelir.
- Yeni bir dil eklemek için çekirdeğe dokunmak gerekmez. İlgili plugin'lere bir `locales/<dil>.toml` dosyası eklemek yeterlidir.

## 5. Repolar ve adlandırma

- **Bu proje:** çekirdek ve `ngui` CLI.
- **`nicegui-core-plugins`:** Tek repo. İçinde her core plugin bir klasördür: `layout-sidebar/`, `storage-sqlite/`, `auth-local/`, `theme-default/`, `store/`. Hepsi tek commit ile birlikte sürümlenir.
- **`nicegui-plugin-<ad>`:** Her özellik plugin'i kendi reposudur. Plugin kimliği `<ad>` kısmıdır: `nicegui-plugin-ai` → `ai`.

Rol dolduran plugin'ler core repoda olmak zorunda değildir. Örneğin `nicegui-plugin-layout-tabs` kendi reposunda durup `provides = "layout"` diyebilir. Core repodaki plugin'ler tek tek açılıp kapatılabilir (`enable/disable`), ama güncelleme ve geri alma işlemleri bütün repo için birlikte yapılır. Lock dosyası **repo başına** bir commit tutar.

**Katalog = adlandırma standardı.** Store, config'de tanımlı kaynaklardaki (ör. bir GitHub kullanıcısı ya da organizasyonu) adı `nicegui-plugin-` ile başlayan repoları listeler. Ayrı bir katalog dosyası tutulmaz. Config'deki kaynaklar bir **liste**dir. Bugün tek kaynak var, yarın başkasının kaynağı eklenebilir.

Otomatik listeleme yalnızca GitHub kaynakları için yapılır. Başka bir git sunucusundaki plugin, doğrudan URL ile kurulabilir: `ngui add https://gitlab.com/x/nicegui-plugin-y`. Böyle kurulan plugin'ler store'da "kurulu" olarak görünür. *(builder kararı)*

Her plugin reposunun (ve core-plugins repo'sundaki her klasörün) kökünde şunlar bulunur:

```toml
# plugin.toml
id = "ai"
name = { tr = "AI Sohbet", en = "AI Chat" }
version = "0.1.0"
description = { tr = "...", en = "..." }
core = ">=1,<2"                 # çekirdek sözleşme sürümü
provides = ""                   # rol dolduruyorsa: "layout" | "storage" | "auth"
requires = ["notes"]            # başka plugin'ler (isteğe bağlı)
dependencies = ["openai>=1.0"]  # pip bağımlılıkları
permissions = ["ai.use"]        # tanımladığı yetkiler
```

Kod `__init__.py` içinde `def setup(ctx): ...` olarak bulunur. Çeviriler `locales/tr.toml` ve `locales/en.toml` dosyalarındadır (bkz. §4.5).

## 6. Kurulum yeri ve durum: `/data` (Docker volume)

Uygulama container içinde çalışır (bkz. §10). Bütün durum, `ngui-data` adlı bir volume'a bağlanan `/data` altında tutulur. Container silinip yeniden oluşturulsa bile kurulu plugin'ler, lock dosyası ve veri kaybolmaz. Bu dokümandaki `~/.ngui` ifadeleri `/data` anlamına gelir. Konum `NGUI_HOME` ortam değişkeni ile değiştirilebilir. Böylece geliştirme sırasında Docker'sız da çalıştırılabilir.

```
/data/
  pydeps/              # plugin'lerin pip bağımlılıkları (uv pip install --target), sys.path'e eklenir
  config.toml          # kaynaklar, etkin plugin'ler, rol atamaları
  plugins.lock         # plugin → repo + commit
  repos/
    core-plugins/      # nicegui-core-plugins klonu
    ai/                # nicegui-plugin-ai klonu
  data/                # storage plugin'inin verisi
```

```toml
# config.toml
default_lang = "tr"
core_repo = "https://github.com/<sahip>/nicegui-core-plugins"
sources   = ["github.com/<sahip>"]
enabled   = ["layout-sidebar", "storage-sqlite", "auth-local", "theme-default", "store", "ai"]
[roles]
layout = "layout-sidebar"
storage = "storage-sqlite"
auth = "auth-local"
theme = "theme-default"
[links]                         # geliştirme kısayolu (bkz. §7)
# ai = "~/code/nicegui-plugin-ai"
```

İlk açılışta `/data` boşsa çekirdek `core_repo`'yu klonlar ve varsayılan seti etkinleştirir.

Her açılışta etkin plugin'lerin `dependencies` alanları `pydeps/` ile karşılaştırılır ve eksikler kurulur. Böylece image yeniden oluşturulsa bile plugin bağımlılıkları kendiliğinden yerine gelir.

## 7. Akışlar

Uygulama container'ın ana komutu olan `ngui run` ile başlar ve tarayıcıdan erişilir. CLI container içinde çalıştırılır: `docker compose exec app ngui add ai`. Çalışan uygulama PID'ini `~/.ngui/ngui.pid` dosyasına yazar.

Her işlemin sonunda uygulama yeniden başlar:
- Store ekranından yapılan işlemlerde uygulama kendini `os.execv` ile yeniden başlatır.
- CLI'dan yapılan işlemlerde CLI dosyaları değiştirir. Uygulama çalışıyorsa PID dosyası üzerinden ona `SIGHUP` gönderir, uygulama da bu sinyalle kendini yeniden başlatır. *(builder kararı)*

İşlemler hem `ngui` CLI'dan hem store ekranından yapılabilir.

| İşlem | Ne olur |
|---|---|
| `ngui add ai` | `nicegui-plugin-ai` repo'su `repos/ai/` altına klonlanır. `dependencies` alanındakiler `uv pip install` ile kurulur. Commit lock dosyasına yazılır, plugin `enabled` listesine eklenir. |
| `ngui remove ai` | Plugin `enabled` listesinden çıkarılır, `repos/ai/` silinir. Veri silinmez (bkz. §9). pip bağımlılıkları kaldırılmaz. |
| `ngui update ai` | `git pull` yapılır, bağımlılıklar yeniden kurulur, yeni commit lock dosyasına yazılır. Önceki commit geri alma için saklanır. |
| `ngui rollback ai` | Lock dosyasındaki önceki commit'e dönülür. |
| `ngui update core` | Core-plugins repo'su güncellenir, hepsi birlikte. Yeni commit'teki bir plugin'in `core` sürümü çalışan çekirdekle uyumsuzsa güncelleme **reddedilir** ve önce `ngui self-update` çalıştırılması istenir. |
| `ngui self-update` | Çekirdeğin kendisi (bu proje bir git reposu olarak) `git pull` ile güncellenir. *(builder kararı)* |
| `ngui enable/disable ai` | Plugin klasörüne dokunulmaz, sadece `enabled` listesi değişir. |
| `ngui use layout layout-tabs` | Bir rolü dolduran plugin değiştirilir. |
| `ngui link ai ~/code/nicegui-plugin-ai` | Plugin doğrudan geliştirme klasöründen çalışır. Push ve update gerekmez. `unlink` ile repo sürümüne dönülür. |
| `ngui new ai` | Şablondan `nicegui-plugin-ai/` iskeleti üretilir. |
| `ngui list` | Etkin, kurulu ve bozuk plugin'leri gösterir. |

**Otomatik güncelleme yoktur.** Uygulama her zaman lock dosyasındaki commit'lerle açılır. Böylece yanlışlıkla push edilen bozuk bir commit uygulamayı düşürmez.

**Geliştirme döngüsü:** Repo yerelde çekilir → `ngui link` → düzenle, yeniden başlat → bitince push → `ngui unlink` → `ngui update`.

## 8. Yükleme sırası ve hata davranışı

1. Config ve lock dosyası okunur, eksik repolar klonlanır.
2. Etkin plugin'lerin `plugin.toml` dosyaları okunur. `core` sürümü uyumsuz olanlar, `requires` alanı karşılanmayanlar ve döngüye girenler **atlanır** ve "bozuk" olarak işaretlenir.
3. Sıralama: önce `storage`, sonra `auth`, sonra `theme`, sonra `layout`, sonra özellik plugin'leri `requires` sırasına göre (topolojik).
4. Her `setup(ctx)` bir `try` bloğu içinde çağrılır. Hata veren plugin atlanır, hata kaydedilir, uygulama açılmaya devam eder. Store bozuk plugin'leri hata mesajıyla gösterir.
5. Bir rol hiç doldurulamazsa çekirdek NiceGUI ile tek bir **kurtarma sayfası** gösterir: hangi rolün eksik olduğunu ve düzeltmek için çalıştırılacak `ngui` komutunu yazar. Bu sayfa layout, auth ya da storage kullanmaz.

## 9. Çok kullanıcılı yapıya hazırlık

- `auth` rolü baştan zorunludur. Plugin'ler tek kullanıcı varsaymaz. Kullanıcıyı her zaman `auth.current_user()` ile, yetkiyi `auth.has()` ile sorar.
- `storage` kapsamı her zaman `(plugin, kullanıcı)` ikilisidir.
- Yetkiler `plugin.toml` dosyasında tanımlanır. Kimin hangi yetkiye sahip olduğuna auth plugin'i karar verir. `auth-local` herkese her yetkiyi verir.
- Bir plugin kaldırıldığında verisi silinmez, tekrar kurulursa geri gelir. Veriyi açıkça silmek store'dan ayrı bir işlem olarak yapılır.

## 10. Docker, servisler ve gateway plugin'leri

**İki tür parça:**
- **Plugin'ler** ana container (`app`) içinde, aynı NiceGUI sürecinde çalışır.
- **Servisler** ayrı container'lardır: API-first backend, Postgres, ileride başka şeyler. NiceGUI'den habersizdirler. Kullanıcı bunları `docker-compose.yml` dosyasına kendisi ekler.

**Gateway plugin'leri** iki dünyayı bağlar. Örnekler: `nicegui-plugin-api-gw`, `nicegui-plugin-db-gw`.
- Sıradan özellik plugin'leridir, sözleşmede özel bir yerleri yoktur.
- Bağlanacakları adresi kendi ayarlarından ya da ortam değişkeninden okurlar. Adres, compose servis adıdır: `postgres:5432`, `http://api:8000`.
- Diğer plugin'lere bir **servis** olarak açılırlar: `ctx.services.provide("db", ...)`. Kullanan plugin `ctx.services.get("db")` ile ister ve gateway'i asla import etmez.
- Plugin reposu, bağlandığı servisin örnek compose bloğunu README'sinde taşır. Kullanıcı bu bloğu kopyalayıp kendi compose dosyasına ekler.

**Bu projede bulunacaklar:**
- `Dockerfile`: Python 3.12, `git`, `uv`, çekirdek. Ana komut `ngui run`.
- `docker-compose.yml`: yalnızca `app` servisi ve `ngui-data` volume'u. Port `127.0.0.1:8080:8080` olarak açılır, yani yalnızca host makineden erişilir. `auth-local` herkesi yönetici saydığı için bu zorunlu. Dışarıya açmadan önce gerçek bir auth plugin'i takılmalı.
- `.env.example`: `GITHUB_TOKEN` (özel repolar ve GitHub listeleme için). Ayrıca ileride gateway'lerin ihtiyaç duyacağı bağlantı bilgileri burada durur.

Uygulama kendini yeniden başlatırken (`os.execv`) container'ın PID'i değişmez, bu yüzden container kapanmaz. Uygulama çökerse compose `restart: unless-stopped` ile yeniden başlatır.

## 11. Kısıtlar

- Python 3.12, NiceGUI (güncel kararlı sürüm), bağımlılık kurulumu için `uv`, çalıştırma ortamı olarak Docker ve Docker Compose.
- Tek süreç. Plugin'lerin pip bağımlılıkları ortak `/data/pydeps` klasörüne kurulur.
- Git container içinde bulunur. Özel repolar için kimlik doğrulama `GITHUB_TOKEN` ortam değişkeninden gelir. Uygulama token'ı diske yazmaz.

## 12. Bilinen bedeller

- Plugin'lerin pip bağımlılıkları çakışabilir, çünkü tek bir ortam var. Kabul edildi. Çakışma kurulum sırasında hata olarak gösterilir.
- Kaldırılan plugin'lerin pip bağımlılıkları ortamda kalır.
- Core plugin'ler birlikte sürümlenir. Birini güncellemek hepsini günceller.
- Plugin'ler tam güvenle çalışır. Sadece güvenilen kaynaklar eklenmelidir.

## 13. Builder'a bırakılanlar

- Sözleşme metotlarının tam isimleri ve imzaları, §4.1'deki anlam korunarak.
- `layout-sidebar` plugin'inin görsel tasarımı.
- `storage-sqlite` plugin'inin şeması.
- GitHub'dan repo listelemenin yöntemi (`gh` ya da REST).
- CLI kütüphanesi seçimi. Standart kütüphanedeki `argparse` tercih edilir.
- `ngui new` şablonunun içeriği.
- `CONTRACT.md`: Çekirdekle birlikte yazılır. Yeni bir plugin yazmak için gereken tek doküman budur.
