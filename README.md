# ngui

NiceGUI uygulaması için küçük bir plugin yükleme çekirdeği. Docker içinde çalışır, durumunu `/data` volume'unda tutar ve yalnızca host'tan (`127.0.0.1:<NGUI_HOST_PORT>`, varsayılan 8080) erişilebilir.

## Kurulum

```sh
cp .env.example .env   # NGUI_CORE_REPO değerini düzenle
docker compose up -d --build
docker compose exec app ngui list
```

`.env` içinde `GITHUB_TOKEN` bulunabilir: `.env` asla commit edilmez ve paylaşılmaz. Host portu 8080 doluysa `.env` içinde `NGUI_HOST_PORT` değerini değiştir.

Core repo tanımlı değilse uygulama kurtarma sayfasını gösterir.

## Kabul testi

```sh
scripts/acceptance.sh
```

Ayrı bir compose projesinde (kendi volume'u, port 18081) gerçek akışı baştan sona dener: core plugin'lerin GitHub'dan çekilmesi, plugin ekleme/kapatma/açma/kaldırma, `sys.exit` çağıran bozuk plugin, `update core`, yeniden başlatma ve yeniden derleme sonrası verinin korunması. Asıl `ngui-data` volume'una dokunmaz. Çekirdekte her değişiklikten sonra çalıştır.

## Yedekleme

Bütün durum (`config.toml`, `plugins.lock`, plugin repoları ve verileri, oturum anahtarı) `/data` volume'undadır. `GITHUB_TOKEN` orada değildir.

```sh
docker compose exec -T app tar czf - -C /data . > ngui-yedek-$(date +%F).tgz
```

Geri yükleme (mevcut `/data` içeriğinin yerini alır):

```sh
docker compose stop app
docker compose run --rm -T app sh -c 'find /data -mindepth 1 -delete && tar xzf - -C /data' < ngui-yedek-TARIH.tgz
docker compose up -d
```

Yedek dosyası oturum anahtarını içerir: paylaşma.

## Plugin geliştirme döngüsü

1. `docker compose exec app ngui --help` ile komutlara bak.
2. `ngui new <ad>` ile iskelet oluştur, `ngui link <ad> <yol>` ile yerel klasörü bağla, işin bitince `ngui unlink`.
   Yayınlanmış plugin'leri `ngui update <ad>` ile güncelle (core plugin'ler için `ngui update core`); `ngui enable <ad>` ile etkinleştir.
3. Değişiklik sonrası uygulama yeniden başlar; hata olursa kurtarma sayfasından bak.

Plugin sözleşmesi (manifest, roller, bus): [CONTRACT.md](CONTRACT.md)
