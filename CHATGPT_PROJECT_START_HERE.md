# BTC_ETH_URA_10YIL — Yeni Sohbet Buradan Başlasın

Bu dosya, ChatGPT Project veya repo üzerinde açılan yeni bir sohbetin zorunlu başlangıç noktasıdır. Amaç konuşma geçmişini ezberlemek değil; yayımlanmış kodu, doğrulanmış çalışma durumunu, kesin ürün kararlarını ve hâlâ öneri olan fikirleri birbirine karıştırmadan devralmaktır.

## 1. Zorunlu okuma sırası

### Python / Investment Engine

1. `CHATGPT_PROJECT_START_HERE.md`
2. `InvestmentEngine-v1.2.0-mobile-ready/docs/PROJECT_MEMORY_BANK.md`
3. `InvestmentEngine-v1.2.0-mobile-ready/docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
4. `InvestmentEngine-v1.2.0-mobile-ready/docs/SESSION_HANDOFF.md`
5. Shadow veya model işi varsa:
   - `InvestmentEngine-v1.2.0-mobile-ready/docs/INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`
   - `InvestmentEngine-v1.2.0-mobile-ready/docs/SHADOW_CHECKPOINT_LOG.md`
6. Değiştirilecek davranışın gerçek kodu, migration'ı, test planı ve runtime çıktısı.

### Quasar

1. `CHATGPT_PROJECT_START_HERE.md`
2. `docs/PROJECT_MEMORY_BANK.md`
3. `docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
4. `docs/SESSION_HANDOFF.md`
5. Python/Shadow bağlamı gerekiyorsa:
   - `docs/INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`
   - `docs/SHADOW_CHECKPOINT_LOG.md`
6. Değiştirilecek page/component/store/service ve ilgili Supabase sözleşmesi.

Ortak bağlam dosyaları iki repoda senkron tutulur. Kod ile belge çelişirse yayımlanmış kod ve runtime kanıtı önceliklidir; çelişki sessizce düzeltilmiş varsayılmaz.

## 2. Yeni sohbet başlangıç mesajı

```text
BTC_ETH_URA_10YIL projesinde bağlamı devral.
Önce CHATGPT_PROJECT_START_HERE.md, PROJECT_MEMORY_BANK.md,
SIGNAL_ENGINE_DECISION_CONTRACT.md ve SESSION_HANDOFF.md dosyalarını tamamen oku.
Python/Shadow işi ise görev takvimi ile SHADOW_CHECKPOINT_LOG.md dosyasını da oku.
RELEASED / APPROVED / PROPOSED / OPEN ayrımını koru.
Sonra iki repoda aktif branch, remote HEAD ve değiştireceğin dosyanın güncel SHA'sını doğrula.
Aksiyon almadan önce kullanıcının son push'ını yeniden oku.
Proje durumu değişirse bitmeden önce handoff'u; kalıcı karar değişirse memory bank veya contract'ı güncelle.
```

## 3. Projenin değişmez amacı

- Gerçek yatırım başlangıcı `25.07.2026`, plan süresi `120 ay`, hedef bitiş `25.07.2036`.
- Aylık DCA/sermaye ayırma ana disiplinidir; sinyal motoru aylık alımı iptal eden veya otomatik portföy yöneten bir robot değildir.
- Python yalnız iki global göreli sistemi değerlendirir: `ETH/BTC` ve `URA/USD`.
- Python seçili Quasar hesabını, kullanıcı bakiyesini veya gerçek çevrilecek adedi okumaz.
- Quasar gerçek `OPENING / CASH_IN / BUY / CONVERSION / SELL / CASH_OUT` hareketlerini seçili yatırım hesabında tutar.
- Otomatik borsa emri yoktur. `LIVE`, uygun yeni kademe için bildirim ve isteğe bağlı order-book gözlemi demektir; alım/satım emri demek değildir.
- `READY`, otomatik LIVE değildir; yalnız manuel production review kapısıdır.
- Validation sonucu threshold, factor weight, mode veya kullanıcı işlemini otomatik değiştirmez.

## 4. Sinyal motorunu yanlış yorumlamama kuralları

1. `direction`, signed edge'in yön etiketidir; `WAIT` veya `NO_ACTION_DATA` ile gelen yön işlem çağrısı değildir.
2. `status=ACTION` günlük model koşuludur; gerçek yeni kademe için ayrıca persistent state içindeki `action_event=true` gerekir.
3. `recommended_size` ve `action_size` global model yüzdesidir; portföy adedi değildir.
4. v1.2.0 `PIT_CORE_REPLAY` etiketi strict FRED-vintage PIT veya production ACTION backtest anlamına gelmez. Doğru yorum: geçmiş tarihe kadar bilinen fiyat/makro observation çekirdeğinin as-of directional replay'i.
5. v1.2.0 calibration gerçek expanding/multi-fold walk-forward değildir; tek kronolojik `%70 train / %30 holdout` keşif raporudur.
6. Replay, production quality/confidence/event kapıları ile K1/K2 state machine'ini birebir doğrulamaz.
7. `model.factor_weights` ve Shadow kriterlerinin `model.parameters` kayıtları DB'de bulunsa da v1.2.0 runtime ağırlıkları `config/defaults.json`dan, readiness kriterlerini ise kod varsayımlarından okur.

## 5. Durum etiketleri

- `RELEASED`: yayımlanmış v1.2.0 kodu/veritabanı davranışı.
- `APPROVED`: kullanıcı tarafından kesinleştirilmiş ürün veya mimari kararı; kodu ayrıca kontrol edilir.
- `PROPOSED`: öneri; kullanıcı onayı olmadan uygulanmaz.
- `OPEN`: kanıt veya karar bekleyen konu.

Özellikle aşağıdakiler hâlâ `PROPOSED/OPEN`dır:

- Kademeler arasında en az 5 karar seansı.
- Ters yöne geçiş için iki ardışık qualified kapanış.
- Production ve replay için tek versioned state machine.
- Python `action_size` ile Quasar kullanıcı limitinin `min(...)` olarak birleştirilmesi.

## 6. Güncel kısa durum

```text
Python model           v1.2.0
Windows Service        RosaInvestmentEngine / RUNNING
Mode                    SHADOW
Realtime Execution     OFF
Görev 1                PASS
Görev 2                PASS
Sıradaki checkpoint    Görev 3 — 01.08.2026 09:30 TRT; sonuç henüz paylaşılmadı

Quasar                 çoklu portföy + account-scoped ledger + append-only revision
Manuel finans testi    100.000 TRY senaryosu hâlâ kullanıcı doğrulaması bekliyor
Draft PR'lar           test döngüsü tamamlanmadan merge edilmez
```

## 7. Remote-first çalışma kuralı

1. Her aksiyon öncesi remote branch ve dosyanın son hali yeniden okunur.
2. Asistan değişikliği mevcut feature/agent branch'e push eder.
3. Kullanıcı `git pull` yapar, yerel test ve manuel finans kontrolünü yürütür.
4. Kullanıcı değişiklik push ettiyse asistan sonraki turda remote'u yeniden okur.
5. Aynı branch üzerinde eşzamanlı yazılmaz.
6. Git ayrışması olduğunda kullanıcıya bir seferde bir komut verilir.
7. Uygulanmış migration geriye dönük değiştirilmez; yeni numara kullanılır.

## 8. Oturum kapanış protokolü

Proje durumunu değiştiren her oturum sonunda `SESSION_HANDOFF.md` şu bilgileri taşımalıdır:

- Ne değişti ve neden?
- Ne gerçekten test/doğrulama gördü?
- Hangi davranış RELEASED, hangi karar APPROVED oldu?
- Hangi fikir PROPOSED/OPEN kaldı?
- Hangi branch ve commit'e push edildi?
- Sıradaki Shadow görevi veya Quasar testi nedir?

## 9. Secret sınırı

API key, parola, Telegram token/Chat ID, Supabase DB password, service-role key veya kişisel secret bağlam belgelerine yazılmaz. Quasar yalnız Project URL ve publishable/anon key kullanır. SecureLS cihaz cache korumasıdır; native keychain veya sunucu secret kasası değildir.

## 10. ChatGPT Project Sources notu

Repo dosyasının varlığı normal sohbetin onu kendiliğinden okuduğunu garanti etmez. Statik Project Source yüklenmişse repo değişince yeniden yüklenmelidir. GitHub connected source kullanılıyorsa yeni sohbet yine dosya yollarını açıkça okuyup branch/HEAD doğrulaması yapmalıdır.
