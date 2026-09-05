# Codex Proje Başlangıcı

Bu repoda analiz veya değişiklik yapmadan önce aşağıdaki dosyaları sırayla ve tamamen oku:

1. `CHATGPT_PROJECT_START_HERE.md`
2. `InvestmentEngine-v1.2.0-mobile-ready/docs/PROJECT_MEMORY_BANK.md`
3. `InvestmentEngine-v1.2.0-mobile-ready/docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
4. `InvestmentEngine-v1.2.0-mobile-ready/docs/SESSION_HANDOFF.md`
5. Python/Shadow işi ise:
   - `InvestmentEngine-v1.2.0-mobile-ready/docs/INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`
   - `InvestmentEngine-v1.2.0-mobile-ready/docs/SHADOW_CHECKPOINT_LOG.md`
6. Değiştirilecek davranışın gerçek kodu, migration'ı ve test planı.

## Zorunlu çalışma kuralları

- Remote branch'in güncel HEAD'ini ve değiştirilecek dosyanın son SHA'sını aksiyon öncesi yeniden oku.
- Kullanıcının son push'ını okumadan yeni değişiklik yapma.
- `RELEASED`, `APPROVED`, `PROPOSED`, `OPEN` ayrımını koru. Öneriyi kullanıcı onayı olmadan kod davranışı sayma.
- Kod ve belge çelişirse yayımlanmış kod/runtime kanıtını esas al; çelişkiyi görünür raporla.
- Aylık DCA ile dönüşüm sinyalini karıştırma. Motor DCA'yı durduran veya otomatik portföy yöneten bir robot değildir.
- Python motoru global ve portföyden bağımsız kalır; seçili Quasar hesabı, bakiye veya gerçek işlem adedi okumaz.
- Python `action_size` yalnız modelin portföyden bağımsız öneri yüzdesidir. Kullanıcının gerçek dönüşüm oranını zorlamaz ve Quasar ile `min(...)` şeklinde sınırlandırılmaz.
- Signal→Conversion bağı tek yönlü ve isteğe bağlıdır: Quasar `decision_id` ile global kararı seçebilir; Python Quasar işlemlerini geri okuyup sinyalini değiştirmez.
- Quasar yüzde butonları hesaplama yardımcısıdır. Sinyal seçilirse önerilen oran ön doldurulabilir fakat kullanıcı tarafından değiştirilebilir; sinyal ID'si elle yazdırılmaz.
- `direction` emir değildir; `ACTION` ile `action_event` farkını koru.
- LIVE otomatik emir değildir; bildirim ve isteğe bağlı order-book gözlemidir.
- `PIT_CORE_REPLAY` etiketini strict vintage PIT veya production ACTION backtest olarak sunma. v1.2.0 historical as-of directional-core replay'dir.
- v1.2.0 calibration'ı gerçek expanding/multi-fold walk-forward diye adlandırma; tek kronolojik `%70/%30` train/holdout raporudur.
- Production K1/K2 state ile replay parity'si kanıtlanmış gibi davranma.
- Runtime factor weight kaynağının `config/defaults.json` olduğunu unutma; `model.factor_weights` tablosunu aktif source of truth sayma.
- Migration 0007 kriterleri `model.parameters`a yazsa da v1.2.0 readiness kodunun hard-coded defaults kullandığını unutma.
- Otomatik emir, otomatik LIVE veya test sonucundan otomatik threshold/weight/mode değişikliği yapma.
- Factor, weight, threshold, status gate, K1/K2, reversal, cooldown veya action-size otoritesi değişirse yeni model version ve yeni Shadow Epoch gerektir.
- Eksik history/source için sentetik score veya quality üretme.
- API key, parola, Telegram token/Chat ID, DB password, service-role key veya kişisel secret'ı repo/dokümana yazma.
- Uygulanmış migration'ı geriye dönük değiştirme; yeni numara kullan ve `migrations/` ile `supabase-migrations/` kopyalarını birebir tut.
- Python release check'in gerçek K1/K2/reversal/parity unit-test paketi yerine geçmediğini açık tut.
- Shadow çıktısını PASS saymadan scheduler/provider/freshness/snapshot/health/job-audit tutarlılığını kontrol et.
- Aynı scheduler job'ını kullanıcı kararı olmadan art arda manuel çalıştırma.
- Git sorununda kullanıcıya bir seferde yalnız bir komut ver; çıktıyı görmeden sonraki komuta geçme.
- Asistan branch'e push eder; kullanıcı pull/test/push yapar; sonraki turda remote yeniden okunur.
- Proje durumu değiştiyse `SESSION_HANDOFF.md`; kalıcı karar değiştiyse memory bank veya signal contract güncellenir.
- Ortak bağlam dosyalarının Quasar reposundaki kopyalarıyla senkronluğunu kontrol et.

## Hâlâ onay bekleyen model önerileri

Aşağıdakileri kullanıcı açıkça onaylamadan uygulama:

1. Kademeler arasında en az 5 karar seansı.
2. Reversal için iki ardışık qualified kapanış.
3. Production/replay için tek versioned state machine.
4. `max_regime_pct` değerinin Python ayar penceresinde düzenlenmesi ve gelecek action-size formülünün kesin bileşenleri.
5. Beş zayıf karar sonrası reset davranışının veri örtüşmesi/idempotency analizi; aynı yön K1 için zorunlu ters rejim kuralı onaylanmış değildir.
