# Codex Proje Başlangıcı

Bu repoda analiz veya değişiklik yapmadan önce aşağıdaki dosyaları sırayla ve tamamen oku:

1. `CHATGPT_PROJECT_START_HERE.md`
2. `docs/PROJECT_MEMORY_BANK.md`
3. `docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
4. `docs/SESSION_HANDOFF.md`
5. Python/Shadow bağlamı gerekiyorsa:
   - `docs/INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`
   - `docs/SHADOW_CHECKPOINT_LOG.md`
6. Değiştirilecek page/component/store/service ve ilgili Supabase sözleşmesi.

## Zorunlu çalışma kuralları

- Remote branch'in güncel HEAD'ini ve değiştirilecek dosyanın son SHA'sını aksiyon öncesi yeniden oku.
- Kullanıcının son push'ını okumadan yeni değişiklik yapma.
- `RELEASED`, `APPROVED`, `PROPOSED`, `OPEN` ayrımını koru. Öneriyi kullanıcı onayı olmadan kod davranışı sayma.
- Kod ve belge çelişirse yayımlanmış kod/runtime kanıtını esas al; çelişkiyi görünür raporla.
- Aylık DCA ile dönüşüm sinyalini karıştırma. Motor DCA'yı durduran veya otomatik portföy yöneten bir robot değildir.
- Python sinyalleri globaldir; Quasar gerçek işlemleri yalnız seçili `account_id` üzerinde uygular ve raporlar.
- `direction` emir değildir; `WAIT/NO_ACTION_DATA` yönünü dönüşüm önerisi gibi sunma.
- `ACTION` ile `action_event` farkını koru. Python `action_size` portföy adedi değildir.
- `PIT_CORE_REPLAY` etiketini strict vintage PIT veya production ACTION backtest olarak sunma.
- v1.2.0 calibration'ı gerçek expanding/multi-fold walk-forward diye adlandırma; tek kronolojik `%70/%30` train/holdout raporudur.
- Production K1/K2 state ile replay parity'si kanıtlanmış gibi davranma.
- Runtime factor weights kaynağı `config/defaults.json`dır; `model.factor_weights` aktif source of truth değildir.
- Signal→Conversion bağı tek yönlü ve isteğe bağlıdır: Quasar global kararı `decision_id` ile kaydedebilir; Python kullanıcı işlemini geri okuyup sinyalini değiştirmez.
- Python `action_size` yalnız düzenlenebilir başlangıç önerisidir. Quasar oranıyla `min(...)` uygulama, hard limit üretme veya kullanıcının gerçek dönüşüm oranını zorlama.
- Sinyal seçimini `AppPopupSelect` ile yaptır; kullanıcıya ID yazdırma. Yüzde butonlarını yalnız bakiye/miktar hesaplama yardımcısı olarak koru.
- Kullanıcı işlemlerinde seçili hesap, önce/işlem/sonra bakiye ve kronolojik replay bütünlüğünü koru.
- Finansal düzeltme/iptal append-only kalır; eski kaydı sessizce update/delete etme.
- Uygulanmış Supabase migration'ı geriye dönük değiştirme; yeni numara kullan ve kardeş Python reposundaki iki migration kopyasıyla uyumu kontrol et.
- API key, parola, Telegram token/Chat ID, DB password, service-role key veya kişisel secret'ı repo/dokümana yazma.
- SecureLS'yi XSS koruması, native keychain veya sunucu secret kasası gibi sunma.
- Quasar doğrulamasında `yarn lint:check` ve `yarn build` sonuçlarını ayrı ayrı raporla; çalıştırmadığın testi geçmiş sayma.
- Manuel 100.000 TRY regression tamamlanmadan finansal hesapları production-doğrulanmış sayma.
- Git sorununda kullanıcıya bir seferde yalnız bir komut ver; çıktıyı görmeden sonraki komuta geçme.
- Asistan branch'e push eder; kullanıcı pull/test/push yapar; sonraki turda remote yeniden okunur.
- Proje durumu değiştiyse `docs/SESSION_HANDOFF.md`; kalıcı karar değiştiyse memory bank veya signal contract güncellenir.
- Ortak bağlam dosyalarının Python reposundaki kopyalarıyla senkronluğunu kontrol et.

## Hâlâ onay bekleyen model/entegrasyon önerileri

Aşağıdakileri kullanıcı açıkça onaylamadan uygulama:

1. Kademeler arasında en az 5 karar seansı.
2. Reversal için iki ardışık qualified kapanış.
3. Production/replay için tek versioned state machine.
4. `max_regime_pct` değerinin Python ayar penceresinde düzenlenmesi ve gelecek action-size formülünün kesin bileşenleri.
5. Beş zayıf karar sonrası reset davranışının veri örtüşmesi/idempotency analizi; aynı yön K1 için zorunlu ters rejim kuralı onaylanmış değildir.
