# Codex Proje Başlangıcı

Bu repoda analiz veya değişiklik yapmadan önce aşağıdaki dosyaları sırayla ve tamamen oku:

1. `CHATGPT_PROJECT_START_HERE.md`
2. `InvestmentEngine-v1.2.0-mobile-ready/docs/PROJECT_MEMORY_BANK.md`
3. `InvestmentEngine-v1.2.0-mobile-ready/docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
4. `InvestmentEngine-v1.2.0-mobile-ready/docs/SESSION_HANDOFF.md`
5. Python/Shadow işi ise:
   - `InvestmentEngine-v1.2.0-mobile-ready/docs/INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`
   - `InvestmentEngine-v1.2.0-mobile-ready/docs/SHADOW_CHECKPOINT_LOG.md`

## Zorunlu çalışma kuralları

- Remote branch'in güncel HEAD'ini ve değiştirilecek dosyanın son halini aksiyon öncesi yeniden oku.
- Kullanıcının son push'ını okumadan yeni değişiklik yapma.
- `RELEASED`, `APPROVED`, `PROPOSED` ve `OPEN` ayrımını koru; öneriyi kullanıcı onayı olmadan bağlayıcı karar veya kod davranışı sayma.
- Python motorunun global/portföyden bağımsız olduğunu koru; seçili Quasar hesabı veya portföy bakiyesi okuma.
- Otomatik emir, otomatik LIVE ve test sonucundan otomatik threshold/weight/mode değişikliği yapma.
- API key, parola, Telegram token/Chat ID, DB password, service-role key veya kişisel sırları repo/dokümana yazma.
- Migration değişecekse uygulanmış dosyayı geriye dönük değiştirme; yeni numara kullan ve `migrations/` ile `supabase-migrations/` kopyalarını birebir tut.
- Python release doğrulamasını ilgili paket kökünden çalıştır; release check'in gerçek K1/K2 unit test paketi yerine geçmediğini unutma.
- Shadow çıktısını `PASS` saymadan scheduler/provider/freshness/snapshot/health/job-audit tutarlılığını kontrol et.
- Aynı scheduler job'ını hata analizinde kullanıcı kararı olmadan art arda manuel çalıştırma.
- Git sorununda kullanıcıya bir seferde yalnız bir komut ver; çıktıyı görmeden sonraki komutu verme.
- Asistan değişikliği branch'e push eder; kullanıcı pull/test/push yapar; sonraki turda remote tekrar okunur.
- Proje durumu değiştiyse bitmeden önce `SESSION_HANDOFF.md`; kalıcı karar değiştiyse memory bank veya signal contract güncellenir.
- Ortak bağlam dosyalarının Quasar reposundaki kopyalarıyla senkronluğunu kontrol et.
