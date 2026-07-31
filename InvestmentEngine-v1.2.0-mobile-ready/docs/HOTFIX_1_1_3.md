# Investment Engine v1.1.3 — Data Semantics, URA ve Realtime Hardening

v1.1.2 smoke testleri core pipeline'ı doğruladı fakat production öncesi dört sınıf eksik gösterdi: eksik factor quality semantics, URA gerçek kaynak coverage'i, realtime'ın ACTION'dan bağımsız test edilememesi ve CLI/provenance/maintenance görünürlüğü.

## 1. Eksik veri artık nötr sayılmıyor

Önceki URA placeholders:

```text
fundamentals score=0 quality=50
breadth      score=0 quality=50
event        score=0 quality=50
```

artık yok. Kaynak/history yoksa `quality=0`. ETH/BTC event provider yoksa da `quality=0`.

Bu nedenle v1.1.3'e geçince URA Data Quality'nin ilk gün düşmesi beklenen ve doğru davranıştır.

Ayrıca `score=0` artık confidence içindeki directional agreement hesabında pozitif oy kabul edilmez. Gerçek nötr factor yalnız kalite/denominator etkisi taşır.

## 2. Global X URA official holdings

Engine URA resmi fund sayfasından dated `Full Holdings (.csv)` linkini otomatik keşfeder ve:

```text
holding_date
ticker
name
weight
shares
market_value
market_price
source_url
```

saklar.

İki snapshot'tan itibaren price-adjusted AUM flow proxy hesaplanabilir. Bu **uranium physical supply-demand değildir**; details alanında açıkça proxy olarak işaretlenir.

## 3. Breadth history

Aynı official holdings CSV'nin günlük constituent market price değerleri zaman içinde birikir. Breadth sentetik olarak başlatılmaz; 2/20/50/200 gözlem eşikleriyle component coverage artar.

## 4. SEC event monitoring

Global X holdings içindeki exact SEC ticker'ları `company_tickers.json` üzerinden CIK'e bağlanır. Recent 8-K/10-Q/10-K/6-K/20-F filing metadata'sı `events.events` içine alınabilir.

Filing bulunması otomatik bullish/bearish anlamına gelmez. v1.1.3 semantic classifier olmadığı için severity=0 saklar. Monitor gerçekten entity kontrol ettiyse “checked and quiet” quality sağlayabilir; coverage yoksa quality=0.

## 5. Realtime smoke test

Yeni komut:

```bat
InvestmentEngineCLI.cmd --test-realtime --realtime-seconds 20
```

Gerçek ACTION üretmeden Coinbase public `level2_batch + matches` zincirini test eder. `market.execution_snapshots` satırları `is_test=true` ve UUID `test_run_id` ile işaretlenir.

Yeni metrikler:

```text
OFI
trade_imbalance
trade_notional_usd
trade_gap_count
sample_window_seconds
```

## 6. CLI

GUI-subsystem onefile EXE korunur. CLI komutlarında MessageBox gösterilmez. Installer `InvestmentEngineCLI.cmd` blocking wrapper'ını da kurar.

## 7. Provenance

Decision tarihinin günlük kapanış tarihi ile derivatives'in canlı gözlem timestamp'i artık `rationale.provenance` içinde ayrı saklanır.

## 8. Weekly / Monthly placeholder kaldırıldı

Weekly: macro + holdings + breadth + SEC refresh.

Monthly: `ACTION/WATCH` kararlarını 5/20/60 trading-session horizonlarında realized direction-adjusted return ile değerlendirir ve `model.performance` yazar. Otomatik weight tuning yapılmaz.

## 9. Migration

Upgrade'de yalnız:

```text
0006_v1_1_3_hardening_realtime_ura.sql
```

çalıştırılır.
