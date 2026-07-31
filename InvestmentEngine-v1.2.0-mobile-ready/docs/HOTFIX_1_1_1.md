# Investment Engine v1.1.1 — Smoke-Test Hotfix

Bu sürüm, ilk gerçek Supabase/Windows smoke testinde görülen üç production sorununu düzeltir.

## 1. Crypto feature insert hatası

v1.1.0'da feature builder'ın metadata alanı olan:

```text
as_of = 2026-07-29
```

`model.features.value` numeric kolonuna feature gibi yazılmaya çalışıyordu. PostgreSQL bu nedenle:

```text
invalid input syntax for type numeric: "2026-07-29"
```

hatası veriyor ve `features → regimes → factor_scores → decisions → signal_state` zinciri başlamadan kesiliyordu.

v1.1.1 yalnız numeric feature'ları `model.features` tablosuna yazar. `as_of` karar tarihinin metadata'sı olarak kullanılmaya devam eder ancak numeric feature satırı değildir.

## 2. Alpha Vantage burst limiti

URA job üç public endpoint kullanır:

```text
TIME_SERIES_DAILY
TIME_SERIES_WEEKLY
TIME_SERIES_MONTHLY
```

v1.1.0 bu üç isteği arka arkaya gönderiyordu. Free key'in burst sınırı nedeniyle weekly/monthly isteği reddedilebiliyordu.

v1.1.1:

- Alpha Vantage istekleri arasında en az 1.25 saniye bırakır.
- `1 request per second` mesajı gelirse bir defaya mahsus ek bekleme + retry yapar.
- Sonsuz retry yapmaz; günlük kota bittiyse hatayı görünür biçimde bırakır.

Free plan günlük kotasını gereksiz tüketmemek için manuel `--once ura` testini tekrar tekrar çalıştırmayın.

## 3. Deribit dış bağlantı hatası

İlk smoke testte `www.deribit.com:443` TCP/HTTPS bağlantısı timeout oldu. Bu bir PostgreSQL veya karar motoru hatası değildir; bağlantı HTTP seviyesine dahi ulaşmadan kesilmiştir.

v1.1.1:

- Deribit için daha kısa connect timeout kullanır.
- BTC ve ETH snapshot'larını birbirinden bağımsız dener.
- Bir varlık başarılıysa `DEGRADED`, ikisi başarısızsa `ERROR` health üretir.
- Deribit hatası Engine'i durdurmaz.
- Crypto karar motoru derivative verisi yoksa derivative factor'u `quality=0` kabul eder; veri kalite eşiği gerektiğinde aksiyonu engeller.

Windows'ta bağlantıyı ayrıca kontrol edin:

```powershell
Resolve-DnsName www.deribit.com
Test-NetConnection www.deribit.com -Port 443
curl.exe "https://www.deribit.com/api/v2/public/ticker?instrument_name=BTC-PERPETUAL"
```

`Test-NetConnection` başarısızsa Windows Firewall, modem/ISP, DNS, proxy veya upstream erişimi araştırılmalıdır.

## 4. Deribit Open Interest birim düzeltmesi

Deribit'in inverse perpetual sözleşmelerinde `open_interest` USD amount units olarak döner. v1.1.0 bunu tekrar index price ile çarparak yanlış normalize ediyordu.

v1.1.1 BTC-PERPETUAL ve ETH-PERPETUAL open interest değerlerini doğrudan USD OI olarak karşılaştırır.

## 5. Windowed EXE CLI çıktısı

Tek EXE GUI için PyInstaller `--windowed` üretildiğinden v1.1.0'da:

```text
InvestmentEngine.exe --service-status
InvestmentEngine.exe --once crypto
```

komutları CMD'ye çıktı basmıyordu.

v1.1.1 parent console'a bağlanmayı dener ve CLI komutlarının sonucunu gösterir. En sağlıklı kullanım **Yönetici olarak açılmış CMD/PowerShell** içindedir.

Örnek:

```bat
cd /d "C:\Program Files\Rosa\InvestmentEngine"
InvestmentEngine.exe --service-status
InvestmentEngine.exe --once crypto
```

`--once` sonunda Supabase `system.job_runs` kaydındaki sonucu da konsola basar.

## Yeniden test sırası

Servisi durdurun:

```bat
InvestmentEngine.exe --stop-service
```

Ardından:

```bat
InvestmentEngine.exe --once macro
InvestmentEngine.exe --once fx
InvestmentEngine.exe --once crypto
InvestmentEngine.exe --once ura
InvestmentEngine.exe --once hourly
```

Sonra Supabase'te:

```sql
select component,status,message,checked_at
from public.engine_health_snapshot
order by component;
```

ve:

```sql
select job_name,started_at,finished_at,status,message
from system.job_runs
order by started_at desc
limit 20;
```

kontrol edin.

Crypto başarılı olduğunda aşağıdakiler artık dolmalıdır:

```sql
select * from model.features where system='ETH/BTC' order by as_of desc, feature_code;
select * from model.regimes where system='ETH/BTC' order by as_of desc;
select * from model.factor_scores where system='ETH/BTC' order by as_of desc, factor_code;
select * from model.decisions where system='ETH/BTC' order by created_at desc;
```

URA başarılı olduğunda aynı zincir `URA/USD` için dolmalıdır.
