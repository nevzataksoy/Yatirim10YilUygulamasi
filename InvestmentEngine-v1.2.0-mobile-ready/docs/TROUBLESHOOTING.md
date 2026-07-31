# Troubleshooting

## Service başlamıyor

```bat
sc query RosaInvestmentEngine
```

ve `logs\investment-engine.log` kontrol edin.

Ayar yoksa EXE'yi yönetici olarak açıp kaydedin.

## Settings yazılamıyor

Kurulum Program Files altındaysa ayar ekranının admin/UAC ile açıldığını doğrulayın. Build `--uac-admin` kullanır.

## DPAPI çözme hatası

settings başka Windows makineden kopyalanmış veya blob bozulmuş olabilir. `settings` + `rosalock` yedeğini saklayıp ayarları yeniden oluşturun.

## Supabase bağlantı hatası

- host/port/user/password,
- SSL mode,
- Session Pooler/direct connection,
- firewall outbound erişimi

kontrol edin.

## Mobil kullanıcı başka kullanıcının verisini görüyor

Bu kritik güvenlik hatasıdır. `0003_mobile_api.sql` RLS migration'ını doğrulayın ve LIVE kullanımı durdurun.


## Tek EXE servis notu
PyInstaller `--onefile` uygulaması servis başlangıcında geçici dizine açılır. Çok yavaş disk/antivirüs taraması nedeniyle Windows 1053 servis zaman aşımı görülürse önce Defender istisnası ve disk performansı kontrol edilmelidir. Sorun devam ederse aynı kaynak kod `--onedir` olarak servis için paketlenebilir; kullanıcı isteği doğrultusunda varsayılan paket `--onefile` kalır.

## v1.1.1 — İlk smoke-test bulguları

### CRYPTO: `invalid input syntax for type numeric: "YYYY-MM-DD"`

Bu hata v1.1.0 feature persistence bug'ıdır. `as_of` metadata'sı numeric `model.features.value` kolonuna yazılıyordu. v1.1.1'e yükseltin; ek migration gerekmez.

### DERIVATIVES: `ConnectTimeout www.deribit.com:443`

Önce işletim sistemi seviyesinde test edin:

```powershell
Resolve-DnsName www.deribit.com
Test-NetConnection www.deribit.com -Port 443
curl.exe "https://www.deribit.com/api/v2/public/ticker?instrument_name=BTC-PERPETUAL"
```

TCP 443 bağlantısı kurulamıyorsa sorun API JSON parser'ı veya Supabase değildir. Firewall/ISP/DNS/proxy/upstream erişimi kontrol edilmelidir. Engine bu durumda çalışmaya devam eder ancak derivative factor data quality düşer.

### URA: Alpha Vantage `1 request per second`

v1.1.1 günlük, haftalık ve aylık URA çağrılarını en az 1.25 saniye aralıkla gönderir. Free key ayrıca günlük çağrı kotasına tabidir. Manuel testleri gereksiz tekrar etmeyin.

### `--service-status` CMD'de sessiz

v1.1.0 `--windowed` EXE'nin stdout'u olmadığı için bu davranış görülür. v1.1.1 parent console'a bağlanır. Komutları Yönetici CMD/PowerShell'den çalıştırın.


## v1.1.2 — FRED tarihleri onlarca yıl eski

Belirti: DGS10=1981, DGS2=1995, VIXCLS=2009 gibi son observation tarihleri. v1.1.1'de finite limit ile ascending FRED verisi alınmasından kaynaklanır. v1.1.2'ye yükseltin, shadow/development ortamında `truncate table macro.observations;` çalıştırın ve `InvestmentEngine.exe --once macro` ile yeniden doldurun.

## Deribit timeout ama OKX çalışıyor

Motor → Derivatives provider = `auto` bırakın. Engine Deribit tam çiftini alamazsa BTC ve ETH'yi birlikte OKX'ten çeker. Testnet (`test.deribit.com`) production karar verisi olarak kullanılmaz.

---

# v1.1.3 — Troubleshooting

## CLI komutu MessageBox açıyor

Bu davranış eski build'e aittir. Kurulum dizinindeki `VERSION` 1.1.3 olmalı ve `InvestmentEngineCLI.cmd` bulunmalıdır. Kullanım:

```bat
InvestmentEngineCLI.cmd --service-status
InvestmentEngineCLI.cmd --once ura
```

v1.1.3 CLI yolu MessageBox kullanmaz. Parent console attach başarısızsa `logs\investment-engine-cli.log` kontrol edilir.

## URA Data Quality upgrade sonrası düştü

Beklenen olabilir. v1.1.2 `fundamentals/breadth/event` eksikken bile q50 veriyordu. v1.1.3 eksik veriyi q0 sayar. İlk Global X holdings snapshot'ta directional holdings flow yoktur; en az iki tarih gerekir. Breadth history de 2/20/50/200 snapshot eşiğinde kademeli gelişir.

## Global X Test başarısız

1. `https://www.globalxetfs.com/funds/ura` erişimini tarayıcı/curl ile kontrol edin.
2. Ayardaki URA Holdings URL override doluysa temizleyip tekrar deneyin.
3. `URA_HOLDINGS` health ve log'u kontrol edin.
4. Dated CSV'yi kalıcı hard-code etmeyin; günlük URL değişebilir.

Global X hatası URA Alpha Vantage price/technical job'ını tek başına düşürmez; holdings factor freshness/quality azalır.

## SEC_EVENTS quality=0

Şu durumlarda normaldir:

- holdings henüz yok,
- top holdings ticker'ları SEC ticker map ile güvenle eşleşmiyor,
- SEC erişimi başarısız.

`CCO CN`, `KAP LI` gibi exchange suffix ticker'lar otomatik cross-listing'e çevrilmez. Yanlış şirket eşleşmesindense quality=0 tercih edilir.

## SEC filing var ama event score=0

v1.1.3 yalnız filing metadata monitoring yapar; filing içeriğini semantik bullish/bearish sınıflandırmaz. `severity=0` bu nedenle bilinçlidir. Monitor health başarılıysa event quality, “kaynak kontrol edildi” bilgisini temsil edebilir.

## Realtime smoke test başarısız

```bat
InvestmentEngineCLI.cmd --test-realtime --realtime-seconds 20
```

sonrasında:

```sql
select * from public.engine_health_snapshot where component='REALTIME_TEST';
```

ve `logs\investment-engine.log` kontrol edilir. Firewall/proxy'nin `wss://ws-feed.exchange.coinbase.com` çıkışına izin vermesi gerekir.

## `--once monthly` OK ama model.performance boş

Normal olabilir. Audit yalnız `ACTION` veya `WATCH` kararlarını, ilgili karar tarihinden sonra 5/20/60 trading-session kapanışı oluşmuşsa değerlendirir. Shadow başlangıcında mature karar bulunmayabilir.
