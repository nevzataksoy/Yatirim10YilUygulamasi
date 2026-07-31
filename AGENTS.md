# Codex Proje Başlangıcı

Bu repoda analiz veya değişiklik yapmadan önce aşağıdaki dosyaları sırayla ve tamamen oku:

1. `CHATGPT_PROJECT_START_HERE.md`
2. `InvestmentEngine-v1.2.0-mobile-ready/docs/PROJECT_MEMORY_BANK.md`
3. `InvestmentEngine-v1.2.0-mobile-ready/docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
4. `InvestmentEngine-v1.2.0-mobile-ready/docs/SESSION_HANDOFF.md`

- Görünür kullanıcı kararlarını, sözleşmedeki durum etiketlerini ve mimari sınırları koru.
- `RELEASED` davranış ile `PROPOSED` veya `OPEN` maddeleri birbirine karıştırma; kullanıcı onayı olmadan öneriyi bağlayıcı karar veya kod değişikliği sayma.
- Proje kararı, doğrulanmış görev sonucu, branch/commit durumu veya açık iş değiştiğinde aynı turda ilgili memory/contract/handoff belgesini güncelle.
- Ortak bağlam belgelerinin Quasar reposundaki kopyalarıyla uyumunu kontrol et.
- API anahtarı, parola, Telegram token/Chat ID, service-role key veya kişisel sırları dokümana yazma.
- Python release doğrulamasını ilgili paket kökünden çalıştır; migration kopyaları varsa birebir eşleşmesini kontrol et.
- Model eşiklerini, ağırlıkları, sinyal state kurallarını veya `engine_mode` değerini test çıktısından otomatik olarak değiştirme.
- Bir oturum proje durumunu değiştirdiyse bitirmeden önce `SESSION_HANDOFF.md` dosyasını güncelle; yeni sohbetlerin yalnız konuşma hafızasına bağımlı kalmasına izin verme.
