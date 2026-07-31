# Investment Engine v1.1.2 — Macro Freshness + Derivatives Fallback

Bu sürüm v1.1.1 smoke testinde ortaya çıkan iki production problemine odaklanır.

## 1. FRED latest-history düzeltmesi

v1.1.1 FRED isteğinde `sort_order=asc` + finite `limit` kullandığı için uzun tarihçeli serilerde son veriler yerine ilk eski kayıtlar gelebiliyordu. Örneğin smoke testte DGS10 1981, DGS2 1995 ve VIXCLS 2009'da kalmıştı.

v1.1.2:

- FRED'i `sort_order=desc` ile çağırır.
- Son 1500 observation'ı ister.
- Gelen veriyi DB'ye yazmadan önce kronolojik sıraya çevirir.
- Karar oluştururken her seri için `observation_date` freshness kontrolü yapar.
- Eski veri API çağrısı başarılı olsa dahi `quality=100` alamaz.

Freshness başlangıç politikası:

- Günlük seriler: <=4 gün 100, <=8 gün 80, <=14 gün 40, >14 gün 0.
- STLFSI4 haftalık: <=10 gün 100, <=17 gün 70, <=24 gün 40, >24 gün 0.

`macro_job` health durumu aggregate freshness quality'ye göre `OK / DEGRADED / ERROR` olur.

## 2. Deribit → OKX fallback

Kullanıcı ağında `www.deribit.com` klasik DNS yolunda hatalı/erişilemez hedefe çözülürken OKX public API erişilebilir bulundu.

v1.1.2 derivatives provider seçenekleri:

- `auto`: Deribit BTC+ETH çiftini dener; herhangi biri başarısızsa ikisini de OKX'ten alır.
- `deribit`: yalnız Deribit.
- `okx`: yalnız OKX.

BTC ve ETH hiçbir zaman farklı provider'lardan karıştırılmaz.

OKX tarafında public veriler:

- BTC-USDT-SWAP / ETH-USDT-SWAP open interest (`oiUsd`)
- funding rate
- mark price
- index price
- ticker bid/ask

Funding dönemi 8 saatten farklıysa oran 8-saat eşdeğerine normalize edilir.

## 3. DB değişikliği

Yeni tablo yoktur. `market.derivatives_snapshots.venue` zaten provider saklayabiliyordu.

Yalnız veri-kaynak metadata'sı için şu migration eklendi:

`0005_v1_1_2_macro_derivatives.sql`

Mevcut v1.1.1 DB üzerinde bunu bir kez çalıştırın.
