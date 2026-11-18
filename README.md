# ngui

NiceGUI uygulaması için küçük bir plugin yükleme çekirdeği. Docker içinde çalışır, durumunu `/data` volume'unda tutar ve yalnızca host'tan (`127.0.0.1:8080`) erişilebilir.

## Kurulum

```sh
cp .env.example .env   # NGUI_CORE_REPO değerini düzenle
docker compose up -d --build
docker compose exec app ngui list
```

Core repo tanımlı değilse uygulama kurtarma sayfasını gösterir.

## Plugin geliştirme döngüsü

1. `docker compose exec app ngui --help` ile komutlara bak.
2. Yeni plugin iskeleti oluştur, düzenle, `ngui enable <ad>` ile etkinleştir.
3. Değişiklik sonrası uygulama yeniden başlar; hata olursa kurtarma sayfasından bak.

Plugin sözleşmesi (manifest, roller, bus): [CONTRACT.md](CONTRACT.md)
