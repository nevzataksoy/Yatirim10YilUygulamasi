# Changelog

## 1.2.0 — CLI, Dependency Preflight ve SEC Coverage Hardening

- CLI wrapper komut sonrası yeni `investment-engine-cli.log` satırlarını terminale replay eder.
- Crypto job stale/missing derivatives için best-effort preflight refresh yapar.
- SEC quality exact eşleşen holdings fon ağırlığı coverageına bağlandı ve SEC-only kapsam için 70 cap eklendi.
- Yeni DB migration yok.

## 1.2.0 — Data Semantics + URA/Realtime Hardening

- Missing factor semantics düzeltildi; veri olmayan event/fundamentals/breadth sentetik quality alamaz.
- Neutral `score=0` factor directional agreement oylamasında pozitif sayılmaz.
- Global X URA resmi full-holdings collector, holdings history ve coverage-aware breadth eklendi.
- SEC ticker/CIK eşleme ve recent filing monitor eklendi; filing yönü sınıflandırılmadığı sürece score nötr kalır.
- Coinbase `level2_batch + matches` execution worker OFI/trade imbalance ile genişletildi.
- `--test-realtime` ACTION üretmeden realtime zincirini doğrular.
- `InvestmentEngineCLI.cmd` blocking terminal wrapper installer'a eklendi; CLI MessageBox kullanmaz.
- Decision provenance timestamps/provider bilgileri eklendi.
- Weekly bakım gerçek holdings/breadth/SEC refresh yapar.
- Monthly audit 5/20/60 session realized performance üretir; weights auto-tune edilmez.
- Regime details market/trend eksenlerine ayrıldı.
- `0006_v1_1_3_hardening_realtime_ura.sql` migration eklendi.

## 1.1.2 — Macro Freshness + Derivatives Fallback

- FRED `sort_order=desc`, recent 1500 observations and chronological persistence.
- Macro observation-date freshness quality; stale values no longer receive full quality.
- `auto / deribit / okx` derivatives provider setting.
- Deribit failure triggers atomic BTC+ETH OKX fallback.
- OKX public OI (`oiUsd`), funding, mark/index and bid/ask support.
- Repository returns the newest complete derivatives pair from one venue.
- Added `0005_v1_1_2_macro_derivatives.sql`.
- Test suite expanded for FRED freshness and OKX fallback.

## 1.1.1 — Smoke-Test Hotfix

- `model.features` numeric kolonuna `as_of` tarih metadata'sının yazılması engellendi.
- Alpha Vantage ücretsiz burst limiti için 1.25 saniyelik request pacing ve tek retry eklendi.
- Deribit collector timeout süresi kısaltıldı ve BTC/ETH bağımsız degrade ediliyor.
- Deribit inverse perpetual open interest birimi düzeltildi; index price ile ikinci kez çarpılmıyor.
- `--windowed` EXE için CLI parent-console bağlantısı ve `--once` job sonucu çıktısı eklendi.
- Regresyon testleri 13 teste çıkarıldı.

## 1.1.1 — Mobile Ready

- Google Sheets ve Apps Script production mimarisinden çıkarıldı.
- `settings` ve `rosalock` EXE klasörüne taşındı.
- Tek PyInstaller EXE hem config UI hem Windows Service host oldu.
- `build.bat` ve `investmentengine_setup.iss` eklendi.
- Ayar ekranı mevcut settings'i parola doğrulamadan decrypt etmeyecek şekilde düzeltildi.
- settings/rosalock ACL SYSTEM + Administrators ile sıkılaştırıldı.
- Supabase Auth + RLS tabanlı mobil portfolio şeması eklendi.
- `public.decision_snapshot` authenticated-only mobil karar yüzeyi oldu.
- Quasar/Capacitor `tr.rosayazilim.yatirimdashboard` backend contract dokümante edildi.

## 1.0.0

- İlk Windows Engine, Supabase, Telegram ve Google Sheets snapshot prototipi.

## 1.2.0

- Model version provenance.
- ETH/BTC point-in-time directional core replay.
- Train/holdout exploratory edge-threshold report.
- Shadow readiness gate and validation snapshots.
- Monthly audit integration.
- CLI wrapper literal-newline packaging bug fixed using real CMD/PowerShell files.
