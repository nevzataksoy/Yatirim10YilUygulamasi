# BTC_ETH_URA_10YIL — Oturum Devir Kaydı

Son güncelleme: 01 Ağustos 2026  
Amaç: Yeni sohbetin son aktif durumu konuşma geçmişini yeniden keşfetmeden devralması.

Kalıcı bağlam `PROJECT_MEMORY_BANK.md`, normatif motor gerçeği `SIGNAL_ENGINE_DECISION_CONTRACT.md`, Shadow adımları görev takvimi, sonuçlar `SHADOW_CHECKPOINT_LOG.md` içindedir.

## 1. Aktif repo/branch'ler

| Repo                                          | Aktif geliştirme branch'i              | Durum            |
| --------------------------------------------- | -------------------------------------- | ---------------- |
| `nevzataksoy/Yatirim10YilUygulamasi`          | `agent/portfolio-audit-reset`          | Draft PR #1 açık |
| `nevzataksoy/tr.rosayazilim.yatirimdashboard` | `feature/initial-investment-dashboard` | Draft PR #1 açık |

HEAD değerleri bu belge güncellendikçe değişir. Yeni oturum her zaman remote HEAD ve değiştireceği dosyanın güncel SHA'sını yeniden doğrular.

## 2. Bu oturumda yapılan bağlam düzeltmesi

İki repodaki başlangıç/memory/contract/handoff belgeleri, gerçek v1.2.0 kodu ve tarihsel hotfix belgeleriyle yeniden karşılaştırıldı.

Düzeltilen ana noktalar:

1. Önceki memory bank mobile-ready kapsamını yanlış biçimde v1.1.1'e topluyordu. Doğru sıra:
   - v1.1.0 mobile-ready temel paket,
   - v1.1.1 gerçek Windows/Supabase smoke-test hotfix'i.
2. `PIT_CORE_REPLAY` kod/DB etiketi strict FRED-vintage PIT değildir. Ürün yorumu historical as-of directional-core replay olarak düzeltildi.
3. v1.2.0 calibration gerçek expanding/multi-fold walk-forward değil, tek `%70 train / %30 holdout` keşif raporudur.
4. Replay'in production quality/confidence/event kapıları ve persistent K1/K2 state machine'iyle parity sağlamadığı açıklaştırıldı.
5. Runtime factor weights kaynağının `config/defaults.json` olduğu; `model.factor_weights` tablosunun v1.2.0 runtime tarafından okunmadığı kaydedildi.
6. Shadow kriterleri migration ile `model.parameters`a seed edilse de v1.2.0 readiness kodunun hard-coded defaults kullandığı kaydedildi.
7. Aylık DCA ile dönüşüm motoru ayrıldı: motor DCA'yı durduran veya otomatik portföy yöneten bir robot değildir.
8. `direction`, `ACTION`, `action_event`, `recommended_size` ve `action_size` kavramları birbirinden ayrıldı.
9. Ham veri → feature → regime → factor → edge/confidence → veto/risk → status → K1/K2 → Supabase tablo zinciri formülleriyle belgelendi.
10. Görev 4–7 sonrasındaki observability, strict PIT, gerçek walk-forward ve manual graduation kilometre taşları netleştirildi.
11. `%50` anlatımı düzeltildi: v1.2.0 `max_regime_pct`, Python'un global kümülatif öneri tavanıdır; Quasar portföyüne uygulanan bağlayıcı bir limit değildir.
12. Signal→Conversion sınırı kesinleştirildi: Quasar isteğe bağlı `decision_id` bağını `AppPopupSelect` ile seçtirir, `action_size` yalnız düzenlenebilir başlangıç oranıdır ve kullanıcı gerçek oranı kendisi belirler.
13. Quasar yüzde butonları ve kayıtlı dönüşüm yüzdeleri hesaplama yardımcılarıdır; Python önerisiyle `min(...)` sözleşmesi uygulanmayacaktır.
14. Beş zayıf karar sonrası resetin ayrı bir beş günlük veri taraması olmadığı, çağrı/evaluation saydığı ve aynı yön qualified ACTION'ın ters rejim olmadan yeni K1 başlatabildiği kaydedildi. Bu davranış görev takvimi bitmeden değiştirilmeyecektir.
15. Canlı karar veri pencereleri koddan çıkarıldı: ETH/BTC yaklaşık `1300` takvim
    günlük ham seri ile 36 ay/52 hafta/60 gün/20 gün/kısa momentum pencerelerini
    birlikte kullanır; derivatives `3` saat, event veto `48/72` saat ve URA
    breadth `2/20/50/200` observation pencerelerine sahiptir. Resetin `5→30`
    yapılmasının yön hesabını değil yalnız persistent state süresini değiştireceği
    açıklaştırıldı. URA günlük history uzunluğunun provider yanıtına bağlı kalması
    sonraki observability/reproducibility hardening için `OPEN` bırakıldı.
16. Görev 7 sonrasında Python veri yaşam döngüsü/retention revizyonu yapılması
    `APPROVED` hedef olarak kaydedildi. Portföy ledger'ı, karar/sinyal bağı,
    fiyat/PIT, performance ve validation kanıtı korunacak; retention süreleri ve
    özet şemaları ölçüm sonrasında kesinleştirilecektir.
17. FRED çoğalmasının kökü koddan doğrulandı: günde dört `macro_job`, sekiz seri ×
    `1500` observation, sabitlenmemiş real-time period ve
    `(series_id, observation_date, realtime_start)` conflict anahtarı. İki günlük
    `14.513` satır örneğinde `4.343` aynı-değer kopyası, `0` gerçek değişim bulundu.
18. FRED current + sıralı append-only change-point + ayrı resmî vintage backfill
    yapısı güçlü bir aday olarak kaydedildi; ancak bu yapı veya doğrudan
    `(series_id, observation_date)` tekilliği onaylanmış nihai politika değildir.
    Önce gerçek FRED üretim/kayıt davranışı, gün içindeki dört çekimin write etkisi,
    seri bazlı revision özellikleri ve geçmiş-veri backtest'i tamamlanacaktır.
19. Quasar Auth/connection kodu tamamlandı: gerçek Auth health testi, authenticated
    user/RLS probe, client/listener/refresh/realtime dispose-re-init, bütün Auth
    event'leri, PKCE confirmation/recovery callback'i ve hata sınıflandırması eklendi.
20. Otomatik service testleri, Prettier/ESLint ve SPA build geçti. Gerçek Supabase
    health/login/RLS/e-posta recovery zinciri ile Capacitor cihaz deep-link testi
    dış ortam gerektirdiği için runtime kanıtı `OPEN` kaldı.
21. FRED tekilleştirme kararı araştırma kapısına alındı: mevcut, yalnız-current,
    current + change-point, resmî vintage PIT ve hibrit adaylar; sinyal çıktısı,
    revision kaybı, look-ahead, write amplification ve 10 yıllık kapasite açısından
    aynı geçmiş veri üzerinde karşılaştırılmadan migration/dedup yapılmayacaktır.
    Dört TRT turu yerel gün varsayımıyla değil, response'taki gerçek
    `realtime_start/realtime_end` değerleriyle sınıflandırılacaktır.
22. Görev 3 kullanıcı logları ve sorgu sonuçlarıyla `PASS` oldu. Weekly/monthly
    scheduler zamanlaması doğru, iki job `OK`, core replay `1383` gözlem ve audit
    threshold/weight değiştirmedi. Readiness'in `NOT_READY` kalması beklenen sonuçtur.
23. Quasar portföy çekirdeği regression paketi eklendi. `100.000 TRY` senaryosunun
    12 ara/final bakiyesi, maliyet/KZ/komisyon, kronolojik replay, çoklu hesap
    izolasyonu, append-only revision/cancellation ve idempotent retry otomatik testte
    `PASS` durumundadır.
24. Finansal kayıtlar store seviyesinde kronolojik bakiye doğrulaması görür. Formlar
    sabit istemci transaction UUID'si taşır; aynı retry çift kayıt üretmez, farklı
    içerikle UUID tekrar kullanımı reddedilir. OPENING satırları tek atomik bulk insert
    olarak kaydedilir.
25. Secret saklamayan `yarn test:acceptance` gerçek Supabase health/login/RLS/token
    refresh/local sign-out kontrolü eklendi. Bu çalışma alanında URL/key/test hesabı
    bulunmadığından gerçek runtime sonucu `OPEN` kaldı; e-posta ve Capacitor deep-link
    ayrıca manuel testtir.

Python model/app kodu, migration, threshold veya factor weight değiştirilmedi.
Quasar uygulama kodu ve Auth dokümantasyonu değişti.

## 3. Python Engine — güncel doğrulanmış operasyon durumu

- Deployed model: **v1.2.0**.
- Windows Service: `RosaInvestmentEngine`, Automatic / Local System.
- Son kullanıcı kanıtı: `STATE : 4 RUNNING`, exit code `0`.
- Mode: `SHADOW`.
- Realtime Execution: `OFF`.
- Crypto history: Coinbase, 2500 ortak gün, `OK`.
- Validation: 1383 historical as-of directional-core observation, core `OK`.
- Configured edge `70` için replay signal sayısı `0`; düşük aday eşiklerde signal count sınırlı.
- Calibration exploratory; hiçbir threshold/weight uygulanmadı.
- URA full replay yeterli PIT history olmadığı için `NOT_READY`.

## 4. Shadow checkpoint'leri

### Görev 1 — `PASS`

- Scheduler hourly, macro, SEC, daily URA ve daily crypto işlerini otomatik çalıştırdı.
- ETH/BTC: `BTC→ETH`, edge `35.640`, confidence `46.250`, quality `90.450`, `WAIT`.
- URA/USD: `URA→USD`, edge `33.990`, confidence `36.170`, quality `70.400`, `NO_ACTION_DATA`.
- Deribit timeout → atomik OKX fallback; derivatives job `OK`.
- Macro quality `97.5`.
- SEC coverage `%14.04`, `DEGRADED`; job çökmemiştir.

### Görev 2 — `PASS`

- 31.07.2026 16:30 TRT TCMB işi zamanında çalıştı.
- Data date `31.07.2026`, USD/TRY `47.4305`.
- FX health/job/snapshot zinciri tutarlı.

### Görev 3 — `PASS`

- `weekly_job` 08:00 TRT ve `monthly_audit_job` 09:00 TRT'de başlayıp `OK` tamamlandı.
- Core replay `1383` gözlem, configured edge `70` sinyali `0`.
- Calibration `LIMITED_SIGNAL_COUNT`; weight/threshold değişmedi.
- `SHADOW_READINESS=NOT_READY`; yalnız üç Shadow günü bulunduğu için beklenen sonuç.
- Recent job success `%97,115`; Görev 4'te üç eski başarısız kayıt ayrıştırılacak.

## 5. Released motor gerçeği

- Minimum quality/edge/confidence `80/70/70`; strong `80/80`.
- Yön label'i emir değildir.
- `ACTION` günlük model status'udur; yeni kademe için `action_event=true` gerekir.
- K1 ilk qualified ACTION'da oluşabilir.
- K2 aynı yön + farklı `as_of` + edge/confidence `80/80` ister.
- K2 için 5-session şartı yoktur.
- Qualified karşı-yön ACTION rejimi hemen çevirebilir.
- Beş zayıf karar aktif state'i resetleyebilir.
- Python global öneri state'inin cumulative cap'i `%50`dir; bu, gerçek portföye bağlayıcı limit değildir.
- Python portföy bakiyesi okumaz ve otomatik emir göndermez.
- LIVE yalnız bildirim/order-book gözlemidir.

## 6. Onay bekleyen model önerileri

Aşağıdakiler `PROPOSED/OPEN` kalır:

1. Kademeler arasında en az 5 karar seansı.
2. Reversal için iki ardışık qualified karşı-yön kapanışı.
3. Production ve replay için tek versioned state machine.
4. `max_regime_pct` değerinin Python ayar penceresinde yönetilmesi ve action-size formülünün kesin strength/quality bileşenleri.
5. Reset sonrası aynı yön K1 davranışının veri örtüşmesi ve idempotency analizi; zorunlu ters rejim kuralı onaylanmış değildir.

Bunlar kullanıcı kararı, yeni model version, test ve yeni Shadow Epoch olmadan uygulanmaz.

## 7. Görevlerden sonra Python yol haritası

### Görev 4 sonrası — davranış değiştirmeyen v1.2.x

- explicit Shadow Epoch,
- run-kind ayrımı,
- expected/actual scheduler run,
- OK/completed rate,
- edge/confidence/quality/status bucket diagnostics,
- mevcut K1/K2/reversal/reset davranışını karakterize eden unit testler,
- JSON/DB runtime configuration authority görünürlüğü.

### Görev 5–6 sonrası

- gerçek expanding/rolling walk-forward,
- strict FRED-vintage PIT,
- production/replay gap/parity raporu,
- URA fundamentals/breadth/event quality decomposition.

### Görev 7

Scheduler, Shadow dağılımları, realtime, historical replay, walk-forward, monthly realized ve URA history birlikte manuel review edilir. READY otomatik LIVE değildir. Model semantiği değişirse yeni version ve yeni Shadow Epoch gerekir.

### Görev 7 sonrası veri hardening

- FRED'in sekiz seri bazında resmî real-time/vintage ve revision davranışını araştır.
- Günlük dört `macro_job` turunda aynı-gün update churn'ü ile günler-arası mantıksal
  kopyaları ayrı ölç; `received/inserted/unchanged/revised/skipped`, WAL/dead-tuple,
  job süresi ve kapasite baseline'ı çıkar.
- Mevcut, yalnız-current, current + append-only change-point, resmî vintage PIT ve
  hibrit adayları geçmiş-veri replay/backtest'inde sinyal, audit ve kapasite
  sonuçlarıyla karşılaştır.
- Yalnız rapor sonrasında tekilleştirme politikasını `APPROVED` yap; doğrudan
  `(series_id, observation_date)` constraint'ine geçme.
- Seçilen politika için mevcut kopyalarda kontrollü dry-run/backfill/dedup ve
  rollback planı oluştur.
- Tablo bazlı korunacak/özetlenecek/silinecek veri matrisi.
- Dry-run kapasite ve etkilenecek satır raporu.
- Portföy, decision, PIT/replay ve Shadow kanıtını koruyan idempotency/bütünlük
  testleri.

Bu iş K1/K2 reseti değildir ve yeni 30 günlük veri toplama beklemesi başlatmaz.

## 8. Quasar — güncel ürün durumu

- Tek Auth kullanıcısı altında çoklu portföy hesabı.
- Global seçili hesap ve account-scoped ledger.
- Seçili hesap/display asset SecureLS/Pinia persistence.
- Dashboard, Portföy, İşlemler, Raporlar ve girişler seçili hesap bazlı.
- Sinyal/market/validation/health global.
- `AppPopupSelect.vue` select standardı.
- Append-only transaction revision/cancellation ve kronolojik bakiye replay kontrolü.
- Kontrollü seçili-portföy reset RPC'si.
- İşlem formlarında önce/işlem/sonra bakiye bağlamı.
- Login ve Settings bağlantı alanlarında yerel ayar şifresi; açık parola saklanmaz.
- Supabase migration `0008` ve `0009` uygulanmış olarak belgelenmiştir; yeni migration `0010+` olmalıdır.
- Signal→Conversion için DB'de isteğe bağlı `portfolio_transactions.decision_id` hazırdır; frontend seçimi henüz uygulanmamıştır.
- Onaylanan UX: sinyal ID'si elle yazılmaz, `AppPopupSelect` kullanılır; seçilen sinyal önerisi forma ön doldurulabilir ama kullanıcı değiştirebilir. Yüzde butonları ve ayar oranları hard limit değildir.
- Otomatik finans testleri `10/10` geçer: 100.000 TRY, ara/final bakiye, maliyet/KZ,
  kronolojik sıra, overdraft, hesap izolasyonu, revision/cancellation ve idempotency.
- Başlangıç portföyü çoklu satırı tek bulk insert; her işlem sabit istemci UUID'siyle
  idempotent retry; store seviyesinde kronolojik bakiye doğrulaması aktiftir.
- `scripts/supabase-acceptance.mjs` gerçek health/login/RLS/refresh/sign-out kontrolünü
  ortam değişkenleriyle çalıştırır ve secret basmaz.

## 9. Quasar'da kullanıcı doğrulaması bekleyen işler

1. Gerçek Supabase test hesabında `yarn test:acceptance` çalıştır; health, login,
   authenticated RLS, refresh ve local sign-out sonucunu doğrula.
2. Confirmation ve password-recovery e-postalarını; Capacitor üretildiğinde cold/warm
   deep-link cihaz akışını manuel doğrula.
3. Çoklu hesap, append-only revision/cancellation ve reset RPC akışını gerçek
   Supabase üzerinde test et.
4. `docs/DEMO_TEST_SCENARIO_100K_TRY.md` içindeki 12 işlemi ekranlardan sırayla uygula;
   ilk sapmada durup ekran görüntüsü paylaş.
5. Dashboard, Portföy, İşlem Geçmişi ve Raporlar toplamlarını otomatik testteki
   beklenen matematikle karşılaştır.
6. Draft PR gerçek ortam test döngüsü tamamlanmadan merge edilmez.
7. Gerçek ortam kabulü sonrasında Signal→Conversion tek yönlü bağını uygula; yalnız
   `ACTION + action_event=true + action_size>0` kararlarını öneri adayı olarak ayır,
   seçim ve oran değişikliği kullanıcıda kalsın.
8. Python reset/reversal/action-size davranışını mevcut Shadow görev takvimi bitmeden değiştirme.

## 10. Yeni oturumun ilk eylemi

1. Zorunlu dört belgeyi tamamen oku.
2. Python işi ise görev takvimi ve checkpoint logunu oku.
3. `RELEASED/APPROVED/PROPOSED/OPEN` ayrımını doğrula.
4. İki remote branch'in güncel HEAD'ini yeniden kontrol et.
5. Kullanıcının son push'ını okumadan dosya değiştirme.
6. Runtime iddiası için gerçek kod veya kullanıcı çıktısı göster.
7. Proje durumu değişirse bu handoff'u; kalıcı karar değişirse memory/contract'ı iki repoda senkron güncelle.

## 11. Güvenlik sınırı

API key, parola, Telegram token/Chat ID, DB password veya service-role secret hiçbir bağlam belgesine yazılmaz. Otomatik emir, otomatik LIVE ve validation sonucundan otomatik threshold/weight değişikliği yoktur.
