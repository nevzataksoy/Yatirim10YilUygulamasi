# Ayarlar ve rosalock — Investment Engine v1.1.3

`settings` ve `rosalock`, **InvestmentEngine.exe ile aynı klasörde** tutulur:

```text
C:\Program Files\Rosa\InvestmentEngine\settings
C:\Program Files\Rosa\InvestmentEngine\rosalock
```

`settings` DPAPI LocalMachine ile şifrelenmiş ayar payload'ıdır. `rosalock` gerçek ayar şifresini saklamaz; salt + PBKDF2-SHA256 doğrulama kaydı içerir. Atomic temp-file + replace yazımı kullanılır.

LocalMachine scope'un amacı Windows Service ve yönetici ayar arayüzünün aynı makinede interaktif parola istemeden aynı encrypted settings'i çözebilmesidir.

## Ayar sekmeleri

### Supabase PostgreSQL

```text
Host / Session Pooler
Port
Database
User
DB Password
SSL Mode
```

### API & Telegram

```text
Alpha Vantage API Key
FRED API Key
Telegram Bot Token
Telegram Chat ID
SEC User-Agent
URA Holdings CSV URL (optional override)
```

URA URL boşsa v1.1.3 resmi Global X URA fund sayfasından güncel Full Holdings CSV'yi otomatik keşfeder.

Ayar penceresinde ayrıca:

```text
Supabase Test
Alpha Vantage Test
FRED Test
Global X Test
SEC Test
Telegram Test
```

bulunur.

### Motor

```text
Çalışma modu: shadow | live | maintenance
Derivatives provider: auto | deribit | okx
Realtime Execution
Execution window
Min Data Quality
Min Edge
Min Confidence
Strong Edge
Strong Confidence
Regime Reset Edge
Regime Reset Days
```

İlk production smoke test:

```text
shadow
auto
Realtime OFF
```

olmalıdır.

`--test-realtime` ayar checkbox'ından bağımsızdır ve ACTION/signal-state yaratmadan bağlantıyı test eder.

## Upgrade

Yeni AppSettings alanları yoksa dataclass default'ları kullanılır. v1.1.2 → v1.1.3 upgrade sırasında mevcut encrypted settings/rosalock silinmez.

Ayar penceresinden kayıt yapılırken çalışan servis varsa yeni ayarları alması için kontrollü restart denenir. Bilerek durdurulmuş servis otomatik açılmaz.
