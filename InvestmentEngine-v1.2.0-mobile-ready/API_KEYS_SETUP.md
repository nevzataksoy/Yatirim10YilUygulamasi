# API / Kimlik Bilgileri — Investment Engine v1.1.3

## Engine için gerekli

### Supabase PostgreSQL
- Host (Direct veya Session Pooler)
- Port 5432
- Database (`postgres` varsayılan)
- User
- Database Password
- SSL Mode `require`

### FRED
`FRED API Key` gerekir.

### Alpha Vantage
`Alpha Vantage API Key` gerekir.

### Telegram
- Bot Token
- Chat ID

Bot adı/username gönderim için zorunlu ayar değildir.

### SEC EDGAR
API key yoktur; kimliği belli eden User-Agent gerekir. Örnek:

```text
NevzatAksoy-InvestmentEngine/1.1 (nevzataksy@gmail.com)
```

Mevcut kaydedilmiş User-Agent'ı sürüm yükseltirken değiştirmeniz gerekmez.

## Engine için key gerektirmeyen kaynaklar

- Coinbase Exchange public market data
- Bitstamp public OHLC
- Deribit public market data
- OKX public market data
- Global X public holdings CSV
- SEC public EDGAR data
- TCMB public kur XML

## URA Holdings CSV URL

Ayar alanı artık opsiyonel override'dır. Boş bırakılırsa engine Global X URA resmi fund sayfasından güncel `Full Holdings (.csv)` bağlantısını keşfeder. Sabit dated CSV URL'yi kalıcı ayar olarak kullanmak önerilmez.

## Derivatives Provider

```text
auto     Deribit tam BTC+ETH → başarısızsa OKX tam BTC+ETH
deribit  yalnız Deribit
okx      yalnız OKX
```

Kullanıcının ağında Deribit production erişimi engelleniyorsa `auto` OKX fallback ile devam eder.

## Gelecek mobil uygulama

Quasar/Capacitor istemci yalnız:

- Supabase Project URL
- Supabase Publishable Key

kullanmalıdır. DB password, service_role/secret key, FRED, Alpha Vantage veya Telegram token mobil uygulamaya konmamalıdır.
