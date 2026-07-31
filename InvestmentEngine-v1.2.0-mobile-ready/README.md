# Rosa Investment Engine v1.2.0 — Production Hardening

Windows üzerinde 7/24 çalışan yatırım karar destek motoru. Ana istemci tarafı Supabase üzerinde tutulur; Windows Engine piyasa/makro verilerini toplar, feature/factor/regime/decision üretir ve ileride Quasar + Capacitor mobil uygulamanın okuyacağı snapshot'ları yazar.

> Otomatik emir göndermez. `live` modu bile yalnız karar/uyarı ve isteğe bağlı execution gözlemi üretir.

## v1.2.0 ile tamamlananlar

- Eksik faktör artık nötr veri sayılmaz: veri yoksa `quality=0`.
- `score=0` factor artık directional agreement hesabında +oy sayılmaz; yalnız pozitif/negatif skorlar agreement oylamasına girer.
- URA için resmi Global X full-holdings CSV otomatik keşfi ve günlük snapshot saklama.
- URA holdings/flow proxy factor'ü: iki farklı tarih oluşmadan directional kalite verilmez.
- URA breadth: holdings CSV içindeki constituent market-price tarihçesinden 1D/20D/50D/200D kapsamı biriktikçe kalite yükselir.
- SEC EDGAR filing monitörü: holdings içindeki güvenle eşleştirilebilen ABD ticker'larını CIK ile izler. Semantik sınıflandırma olmadığı için filing'lere sahte yön skoru verilmez.
- ETH/BTC event provider bağlı değilse `event quality=0`.
- Coinbase realtime smoke test: ACTION üretmeden `level2_batch + matches` ile spread, depth, OBI, OFI, microprice ve trade imbalance test edilir.
- CLI komutları için MessageBox kaldırıldı; `InvestmentEngineCLI.cmd` blocking terminal wrapper olarak installer'a eklendi.
- Decision provenance: kapanış tarihi, değerlendirme zamanı, price provider, derivatives observed_at ve macro observation dates ayrıştırıldı.
- Weekly job artık macro + Global X holdings/breadth + SEC refresh yapar.
- Monthly audit mature `ACTION/WATCH` kararlarını 5/20/60 trading-session horizonlarında değerlendirip `model.performance` yazar; factor ağırlıklarını otomatik değiştirmez.
- Regime iki eksende açıklanır: `market_regime` ve `trend_regime`; legacy `primary_regime` weight seçimi için korunur.

## Kurulum/upgrade sırası

Yeni kurulum: `0001` → `0006` migration'larını sırayla çalıştırın.

v1.1.2'den upgrade: yalnız `migrations/0006_v1_1_3_hardening_realtime_ura.sql` çalıştırın, sonra `build.bat` ile oluşturulan `InvestmentEngineSetup-1.2.0.exe` dosyasını mevcut kurulumun üzerine kurun.

İlk doğrulama ayarları:

```text
Engine Mode            = shadow
Realtime Execution     = OFF
Derivatives Provider   = auto
URA Holdings CSV URL   = boş (otomatik resmi Global X keşfi)
```

Terminal komutlarında önerilen kullanım:

```bat
cd /d "C:\Program Files\Rosa\InvestmentEngine"
InvestmentEngineCLI.cmd --service-status
InvestmentEngineCLI.cmd --once ura
InvestmentEngineCLI.cmd --once events
InvestmentEngineCLI.cmd --test-realtime --realtime-seconds 20
```

## Bilinçli sınırlar

`fundamentals` faktörünün v1.2.0 içeriği Global X URA ETF holdings/flow proxy'sidir; doğrudan uranium spot fiyatı, term contracting veya maden arz-talep modeli değildir. Bu ayrım factor details içinde saklanır.

Crypto event/news sentiment provider henüz bağlanmadı; ETH/BTC `event quality=0` ile güvenli biçimde eksik sayılır. SEC filing ingestion da semantik bir model değildir: izleme yapılmışsa kalite sağlar, fakat filing içeriğini otomatik bullish/bearish olarak uydurmaz.

Ayrıntılar: `HOTFIX_1_1_3.md`, `TEST_PLAN_V1_1_3.md`, `MODEL_AND_SCHEDULE.md`, `INSTALL_WINDOWS_SERVER.md`. Bilinçli açık kapsam `OPEN_ITEMS_AFTER_V1_1_3.md` içinde takip edilir.

## v1.2.0 Model Validation

```bat
InvestmentEngineCLI.cmd --validate-model
```

ETH/BTC point-in-time directional core replay, exploratory calibration ve Shadow readiness raporunu üretir. Parametre veya çalışma modu otomatik değiştirilmez. Ayrıntı: `MODEL_VALIDATION_AND_SHADOW.md`.
