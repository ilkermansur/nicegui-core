# Yapılacaklar

## Plugin'ler

- [ ] **`nicegui-plugin-auth-password`: parola ile giriş yapan auth rol plugin'i.** `auth-local`'ın yerine `ngui use auth auth-password` ile takılır; çekirdek değişmez.
  - Giriş/çıkış sayfası; giriş yapmamış istekler girişe yönlendirilir (oturum `app.storage.user`'da).
  - Parolalar tuzlu hash ile (`hashlib.scrypt`), asla düz metin.
  - İlk açılışta kullanıcı yoksa ilk yönetici hesabı oluşturulur.
  - Roller → yetkiler; `admin` her yetkiye sahip. `users.manage` yetkili kullanıcı yönetimi sayfası.
  - Dikkat: roller depolama → kimlik → tema → layout sırasıyla yüklenir; giriş sayfası layout çerçevesinin dışında çizilir (sözleşmedeki tek bilinçli istisna, README'de açıklanır). Kurtarma modunda da çalışmalı.
  - Bitti sayılması için: `skills/ngui-plugin` ile yazılmış, testleri (hash, yetki, girişe yönlendirme, dil dosyaları) ve CI'ı var, `ngui link` ile denenmiş (ilk yönetici, çıkış/giriş, yönetici olmayan mağazaya giremiyor).
