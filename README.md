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

## Plugin geliştirme döngüsü

1. `docker compose exec app ngui --help` ile komutlara bak.
2. `ngui new <ad>` ile iskelet oluştur, `ngui link <ad> <yol>` ile yerel klasörü bağla, işin bitince `ngui unlink`.
   Yayınlanmış plugin'leri `ngui update <ad>` ile güncelle (core plugin'ler için `ngui update core`); `ngui enable <ad>` ile etkinleştir.
3. Değişiklik sonrası uygulama yeniden başlar; hata olursa kurtarma sayfasından bak.

Plugin sözleşmesi (manifest, roller, bus): [CONTRACT.md](CONTRACT.md)
