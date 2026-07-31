# Supabase Kurulumu — Investment Engine v1.1.3

Bu rehber, **Rosa Investment Engine Windows servisinin Supabase PostgreSQL veritabanına bağlanması** ve gelecekteki **`tr.rosayazilim.yatirimdashboard` Quasar/Capacitor mobil uygulamasının Supabase Auth + Data API kullanması** için gereken Supabase ayarlarını adım adım açıklar.

> Menü adları 30.07.2026 tarihindeki güncel Supabase Dashboard terminolojisine göre yazılmıştır. Arayüzde küçük isim/konum değişiklikleri olabilir; ancak `Connect`, `Database`, `SQL Editor`, `Authentication` ve `Settings → API Keys` güncel resmi dokümantasyonda kullanılan ana bölümlerdir.

---

# 1. Bu projede Supabase ne için kullanılıyor?

Supabase üç görev üstlenir:

1. **PostgreSQL veritabanı**
   - Windows Server üzerinde çalışan `InvestmentEngine.exe` piyasa, faktör, karar, health ve kullanıcı portföy verilerini buraya yazar/okur.

2. **Supabase Auth**
   - Gelecekte Android/Quasar uygulamasında kullanıcı email + parola ile giriş yapar.
   - Kullanıcı yalnız kendi portföyünü, işlemlerini ve yatırım ayarlarını görür.

3. **Data API + RLS**
   - Mobil uygulama PostgreSQL kullanıcı/parolası kullanmaz.
   - Mobil uygulama yalnız Project URL + Publishable Key + Supabase Auth oturumu kullanır.

Windows Engine ise PostgreSQL bağlantısını doğrudan kullanır.

---

# 2. Hangi bilgiyi nereden alacağız?

## Windows Investment Engine için

| Investment Engine alanı | Supabase'te bulunacağı yer |
|---|---|
| Host / Session Pooler | `Project → Connect → Session pooler → View parameters → Host` |
| Port | Aynı bölüm → `5432` |
| Database | Aynı bölüm → genellikle `postgres` |
| Kullanıcı | Aynı bölüm → genellikle `postgres.PROJECT_REF` |
| DB Parolası | Proje oluştururken belirlenen Database Password; unutulduysa `Database → Settings` üzerinden reset |
| SSL Mode | Supabase'ten alınmaz; Engine'de `require` kullanın |

## Gelecekteki mobil uygulama için

| Mobil uygulama alanı | Supabase'te bulunacağı yer |
|---|---|
| Supabase Project URL | `Project → Connect → Project URL` |
| Publishable Key | `Project → Connect → Publishable key` veya `Settings → API Keys` |

> Mobil uygulamaya **Database Password, Secret Key veya legacy `service_role` key kesinlikle konulmaz.**

---

# 3. Supabase projesi oluşturma

1. Supabase Dashboard'u açın.
2. Organizasyonunuzu seçin.
3. **New project** seçeneğine tıklayın.
4. Project Name girin.
5. Güçlü bir **Database Password** belirleyin.
6. Region seçin.
7. Free plan ile başlayabilirsiniz.
8. Projenin oluşmasını bekleyin.

Örnek proje adı:

```text
rosa-investment-engine
```

Database Password'u güvenli bir parola yöneticisinde saklayın. Bu parola Windows Engine'in PostgreSQL bağlantısında kullanılacaktır.

---

# 4. Database Password'u unuttuysanız

Supabase mevcut veritabanı parolasını açık metin olarak tekrar göstermeyebilir.

Menü yolu:

```text
Project
→ Database
→ Settings
→ Database Password
```

Burada arayüze göre `Reset database password` benzeri düğme görürsünüz.

Parolayı resetlediğinizde:

1. `InvestmentEngine.exe` açın.
2. Ayar şifresi ile Settings ekranına girin.
3. **DB Parolası** alanını değiştirin.
4. **Supabase Test** çalıştırın.
5. Kaydedin.

Harici backend'ler eski parolayı kullanıyorsa onlar da güncellenmelidir.

---

# 5. Windows Server için bağlantı bilgilerini alma

Windows Server'daki Engine kalıcı çalışan bir backend olduğu için, özellikle IPv4 ortamında **Session Pooler** kullanacağız.

Menü yolu:

```text
Project Dashboard
→ Connect
```

Açılan panelde:

```text
Session pooler
```

bölümünü bulun.

Varsa:

```text
View parameters
```

seçeneğini açın.

Burada Host, Port, Database ve User alanları görünür.

Supabase size şu biçimde bir connection string de gösterebilir:

```text
postgresql://postgres.PROJECT_REF:[YOUR-PASSWORD]@aws-0-REGION.pooler.supabase.com:5432/postgres
```

---

# 6. Connection string'i Engine alanlarına ayırma

Örnek:

```text
postgresql://postgres.abcdxyz123:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
```

Bunun karşılığı:

```text
Host / Session Pooler:
aws-0-eu-central-1.pooler.supabase.com

Port:
5432

Database:
postgres

Kullanıcı:
postgres.abcdxyz123

DB Parolası:
<proje Database Password>

SSL Mode:
require
```

## Host

`@` işaretinden sonraki ve `:5432` öncesindeki bölüm:

```text
aws-0-eu-central-1.pooler.supabase.com
```

## Port

Session Pooler:

```text
5432
```

## Database

Varsayılan:

```text
postgres
```

## User

Genellikle:

```text
postgres.PROJECT_REF
```

> Session Pooler kullanırken sadece `postgres` yazmayın. `Connect → Session pooler → View parameters → User` değerini aynen kopyalayın.

## Password

`[YOUR-PASSWORD]` yerine proje Database Password'u kullanılır.

## SSL

Engine:

```text
require
```

kullanacak şekilde hazırlanmıştır.

---

# 7. Ayar ekranına örnek giriş

Supabase `Connect` paneli:

```text
Host: aws-0-eu-central-1.pooler.supabase.com
Port: 5432
Database: postgres
User: postgres.xxxxxxxxxxxxxxxxxxxx
```

Investment Engine:

```text
Supabase PostgreSQL
────────────────────────────────────────
Host / Session Pooler:
aws-0-eu-central-1.pooler.supabase.com

Port:
5432

Database:
postgres

Kullanıcı:
postgres.xxxxxxxxxxxxxxxxxxxx

DB Parolası:
********

SSL Mode:
require
```

Sonra:

```text
Supabase Test
```

butonuna basın.

Başarılıysa bağlantı tarafı tamamdır.

---

# 8. Session Pooler mı Direct Connection mı?

## Session Pooler — önerilen

```text
aws-...pooler.supabase.com:5432
```

Özellikle:

- Windows Server IPv4 kullanıyorsa,
- Engine kalıcı backend ise,
- Supabase Free kullanılıyorsa,

önerilen seçimdir.

## Direct Connection

Örnek:

```text
db.PROJECT_REF.supabase.co:5432
```

Supabase Free projelerde direct endpoint varsayılan olarak IPv6 tarafındadır. Windows Server'ın internet bağlantısı IPv6 desteklemiyorsa bağlantı başarısız olabilir.

Bu yüzden ilk kurulumda:

```text
Session Pooler / 5432
```

kullanın.

---

# 9. Transaction Pooler kullanmayın

Transaction Pooler genellikle:

```text
6543
```

portunu kullanır ve kısa ömürlü/serverless bağlantılar içindir.

Investment Engine:

```text
Windows Service
→ 7/24
→ persistent DB pool
```

olduğu için bizim varsayılanımız:

```text
Session Pooler
Port 5432
```

---

# 10. Migration dosyalarını sırayla çalıştırma

Paket:

```text
migrations/
├── 0001_schema.sql
├── 0002_seed.sql
├── 0003_mobile_api.sql
├── 0004_v1_1_hardening.sql
├── 0005_v1_1_2_macro_derivatives.sql
└── 0006_v1_1_3_hardening_realtime_ura.sql
```

İlk kurulumda bu altı dosyayı sırayla çalıştırın.

---

# 11. 0001_schema.sql

Menü:

```text
Project
→ SQL Editor
→ New query
```

1. Yerel projedeki `migrations/0001_schema.sql` dosyasını açın.
2. Tüm içeriği kopyalayın.
3. SQL Editor'a yapıştırın.
4. **Run** butonuna basın.
5. Hata olmadığını kontrol edin.

Bu migration:

```text
market
macro
fundamentals
events
model
system
```

şemalarını ve Engine çekirdek tablolarını oluşturur.

Ayrıca gerekirse:

```text
pgcrypto
```

extension'ını açar.

---

# 12. 0002_seed.sql

Menü:

```text
SQL Editor
→ New query
```

`0002_seed.sql` içeriğini yapıştırıp **Run** deyin.

Bu migration:

- Coinbase
- Bitstamp
- Alpha Vantage
- Deribit
- FRED
- SEC
- TCMB

kaynaklarını `system.data_sources` tablosuna ekler.

Ayrıca:

```text
min_data_quality
min_action_edge
min_action_confidence
strong_action_edge
strong_action_confidence
regime_reset_edge
regime_reset_days
base_tranche_pct
max_regime_pct
```

gibi model parametrelerini seed eder.

---

# 13. 0003_mobile_api.sql

Menü:

```text
SQL Editor
→ New query
```

`0003_mobile_api.sql` çalıştırın.

Mobil uygulama tarafında oluşturulan temel yapılar:

```text
public.profiles
public.investment_accounts
public.portfolio_transactions
public.user_investment_settings
public.portfolio_positions
```

Engine'in mobil Dashboard'a açacağı snapshot tabloları:

```text
public.market_snapshot
public.decision_snapshot
public.decision_history
public.engine_health_snapshot
```

Supabase Auth kullanıcısı oluşunca otomatik:

```text
profil
Ana Portföy
varsayılan yatırım ayarları
```

oluşturan trigger da burada kurulur.

---

# 14. 0004_v1_1_hardening.sql

Menü:

```text
SQL Editor
→ New query
```

`0004_v1_1_hardening.sql` çalıştırın.

Bu migration staged-action sistemini garanti eder:

```text
action_event
action_stage
action_size
regime_cumulative_size
model.signal_state
```

Eski v1.0 DB'yi v1.1'e yükseltmek için hazırlanmıştır; fresh kurulumda da güvenle çalıştırılır.

---


# 15. 0005_v1_1_2_macro_derivatives.sql

Menü:

```text
SQL Editor
→ New query
```

`0005_v1_1_2_macro_derivatives.sql` çalıştırın.

Bu migration yeni tablo oluşturmaz. Mevcut `market.derivatives_snapshots.venue` alanını kullanarak:

- `OKX` veri kaynağı metadata'sını ekler,
- Deribit'i AUTO/fallback mimarisine göre işaretler,
- FRED veri kaynağı notunu freshness kontrolünü yansıtacak şekilde günceller.

Mevcut verileri silmez. v1.1.1 → v1.1.2 upgrade sırasında bir kez çalıştırılmalıdır.

---


# 15A. 0006_v1_1_3_hardening_realtime_ura.sql

Menü:

```text
SQL Editor
→ New query
```

`0006_v1_1_3_hardening_realtime_ura.sql` çalıştırın.

Bu migration:

- URA official holdings için `market_price` kolonunu ekler,
- realtime execution snapshot'a OFI/trade imbalance/trade-gap ve test-run alanlarını ekler,
- Global X URA holdings ve Coinbase realtime data-source metadata'sını tanımlar.

Mevcut verileri silmez. v1.1.2 → v1.1.3 upgrade sırasında yalnız bu migration gerekir.

---

# 16. Migration sonrası şemaları kontrol etme

Menü:

```text
SQL Editor
→ New query
```

Sorgu:

```sql
select schema_name
from information_schema.schemata
where schema_name in (
  'market',
  'macro',
  'fundamentals',
  'events',
  'model',
  'system'
)
order by schema_name;
```

Beklenen:

```text
events
fundamentals
macro
market
model
system
```

---

# 16. Engine tablolarını kontrol etme

```sql
select table_schema, table_name
from information_schema.tables
where table_schema in (
  'market',
  'macro',
  'fundamentals',
  'events',
  'model',
  'system'
)
order by table_schema, table_name;
```

Önemli tablolar arasında şunlar olmalıdır:

```text
market.daily_prices
market.derivatives_snapshots
market.execution_snapshots
macro.observations
fundamentals.ura_holdings
fundamentals.ura_breadth
events.events
model.features
model.regimes
model.factor_scores
model.decisions
model.signal_state
model.performance
model.parameters
system.data_sources
```

---

# 17. Seed kontrolü

```sql
select
  code,
  category,
  expected_interval_seconds,
  stale_after_seconds,
  required
from system.data_sources
order by code;
```

Beklenen kaynaklar:

```text
ALPHA_URA
BITSTAMP_DAILY
COINBASE_DAILY
DERIBIT
FRED
SEC
TCMB
```

Parametre kontrolü:

```sql
select
  system,
  parameter_key,
  value_numeric,
  description
from model.parameters
order by system, parameter_key;
```

---

# 18. Mobil tabloları kontrol etme

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
and table_name in (
  'profiles',
  'investment_accounts',
  'portfolio_transactions',
  'user_investment_settings',
  'market_snapshot',
  'decision_snapshot',
  'decision_history',
  'engine_health_snapshot'
)
order by table_name;
```

Hepsi listelenmelidir.

---

# 19. Table Editor'da tabloları görme

Menü:

```text
Project
→ Table Editor
```

Schema seçici mevcutsa:

```text
public
market
model
system
...
```

arasında geçiş yapabilirsiniz.

`public`:

```text
profiles
investment_accounts
portfolio_transactions
user_investment_settings
market_snapshot
decision_snapshot
decision_history
engine_health_snapshot
```

`model`:

```text
features
factor_scores
regimes
decisions
signal_state
```

---

# 20. Supabase Auth yapılandırması

Gelecekte mobil uygulama kullanıcı girişini Supabase Auth ile yapacaktır.

Menü:

```text
Authentication
→ Sign In / Providers
```

Dashboard sürümüne göre `Authentication → Providers` olarak da görünebilir.

İlk mobil sürüm:

```text
Email
```

provider kullanacaktır.

Kontrol:

```text
Email provider = Enabled
```

Production'da:

```text
Confirm Email = Enabled
```

önerilir.

---

# 21. Kullanıcıları nereden göreceğiz?

Menü:

```text
Authentication
→ Users
```

Mobil uygulamadan register olan kullanıcı burada görünür.

Temel kimlik:

```text
auth.users.id
```

UUID'sidir.

Bizim:

```text
public.profiles.user_id
public.investment_accounts.user_id
public.portfolio_transactions.user_id
```

alanları bu kimliği kullanır.

---

# 22. Dashboard'dan test kullanıcısı oluşturma

Menü:

```text
Authentication
→ Users
→ Add user
```

Arayüze göre:

```text
Create new user
```

veya:

```text
Send invitation
```

seçeneklerinden biri bulunabilir.

Test kullanıcı oluşturduktan sonra:

```sql
select * from public.profiles order by created_at desc;
select * from public.investment_accounts order by created_at desc;
select * from public.user_investment_settings order by created_at desc;
```

Yeni kullanıcı için:

```text
profil
Ana Portföy
yatırım ayarları
```

oluşmuş olmalıdır.

---

# 23. RLS kontrolü

```sql
select
  schemaname,
  tablename,
  rowsecurity
from pg_tables
where schemaname = 'public'
and tablename in (
  'profiles',
  'investment_accounts',
  'portfolio_transactions',
  'user_investment_settings'
)
order by tablename;
```

`rowsecurity`:

```text
true
```

olmalıdır.

---

# 24. Project URL nereden alınır?

Bu bilgi **Windows Engine için gerekli değildir**.

Gelecekte mobil uygulamanın Supabase client'ı için kullanılacaktır.

Menü:

```text
Project Dashboard
→ Connect
```

Burada:

```text
Project URL
```

alanını bulun.

Örnek:

```text
https://abcdefghijklmnopqrst.supabase.co
```

Quasar uygulamada:

```text
Supabase Project URL
```

alanına girilecektir.

---

# 25. Publishable Key nereden alınır?

Yöntem 1:

```text
Project Dashboard
→ Connect
→ Publishable key
```

Yöntem 2:

```text
Project Dashboard
→ Settings
→ API Keys
```

Burada:

```text
Publishable and secret API keys
```

bölümünü bulun.

Yeni key yoksa arayüzde:

```text
Create new API keys
```

seçeneği bulunabilir.

Mobil uygulamada kullanılacak key:

```text
sb_publishable_...
```

---

# 26. Hangi key mobil uygulamaya konulacak?

DOĞRU:

```text
Publishable Key
sb_publishable_...
```

MOBİLE KONULMAZ:

```text
Secret Key
sb_secret_...
```

MOBİLE KONULMAZ:

```text
legacy service_role
```

Secret/service-role anahtarları yüksek yetkilidir ve RLS bypass edebilir.

Windows Engine'in de bu key'lere ihtiyacı yoktur; Engine PostgreSQL kullanıcı/parolasıyla bağlanır.

---

# 27. Legacy anon/service_role görürseniz

Yeni Supabase key sistemi:

```text
Publishable Key
Secret Key
```

şeklindedir.

Legacy:

```text
anon
service_role
```

key'leri eski sistemdir.

Gelecekteki mobil uygulamayı:

```text
Publishable Key
```

üzerine kuracağız.

---

# 28. Mobil Auth Redirect URL

Quasar/Capacitor projesine geçtiğimizde:

```text
Authentication
→ URL Configuration
```

bölümünü kullanacağız.

Burada:

```text
Site URL
Redirect URLs
```

alanları vardır.

Mobil deep-link URI kesinleştiğinde örneğin:

```text
tr.rosayazilim.yatirimdashboard://auth/callback
```

benzeri URI eklenecektir.

Bu alanı şu anda doldurmak zorunda değilsiniz.

---

# 29. Engine ayar ekranında Project URL neden yok?

Bilinçli tasarım:

Windows Engine:

```text
PostgreSQL Host
Port
Database
User
Password
SSL
```

kullanır.

Mobil uygulama:

```text
Project URL
Publishable Key
Auth JWT
```

kullanır.

Bu iki güvenlik alanı birbirinden ayrıdır.

---

# 30. Host alanına ne yazılmamalı?

YANLIŞ:

```text
https://abcxyz.supabase.co
```

Bu **Project URL**'dir; PostgreSQL Host değildir.

DOĞRU:

```text
aws-0-....pooler.supabase.com
```

Ayrıca DB Password alanına:

```text
Publishable Key
Anon Key
Secret Key
Service Role Key
```

yazılmaz.

---

# 31. En sık hata — kullanıcı adı

Session Pooler user genellikle:

```text
postgres.PROJECT_REF
```

şeklindedir.

Daima:

```text
Connect
→ Session pooler
→ View parameters
→ User
```

değerini kopyalayın.

---

# 32. En sık hata — port

Bizim Engine:

```text
Session Pooler
Port 5432
```

kullanır.

`6543` transaction pooler portudur ve varsayılan Engine bağlantımız değildir.

---

# 33. Supabase Test başarısızsa

Sırayla kontrol edin:

1. Host `aws-...pooler.supabase.com` biçiminde mi?
2. Session Pooler mı?
3. Port `5432` mi?
4. Database `postgres` mi?
5. User `postgres.PROJECT_REF` biçiminde mi?
6. Database Password doğru mu?
7. SSL mode `require` mı?
8. Windows Server internete çıkabiliyor mu?
9. Firewall outbound TCP 5432'yi engelliyor mu?

Paroladan emin değilseniz:

```text
Database → Settings → Reset database password
```

ile yenileyin.

---

# 34. Engine çalıştıktan sonra fiyat verisini kontrol etme

```sql
select *
from market.daily_prices
order by fetched_at desc
limit 20;
```

---

# 35. Derivatives verisini kontrol etme

```sql
select *
from market.derivatives_snapshots
order by observed_at desc
limit 20;
```

---

# 36. Makro verisini kontrol etme

```sql
select *
from macro.observations
order by fetched_at desc
limit 20;
```

---

# 37. Kararları kontrol etme

```sql
select
  id,
  created_at,
  as_of,
  system,
  direction,
  status,
  regime_code,
  edge_score,
  confidence,
  uncertainty,
  data_quality,
  risk_score,
  action_event,
  action_stage,
  action_size,
  regime_cumulative_size
from model.decisions
order by created_at desc
limit 20;
```

---

# 38. Mobil snapshot tablolarını kontrol etme

```sql
select * from public.market_snapshot order by symbol;
```

```sql
select * from public.decision_snapshot order by system;
```

```sql
select *
from public.engine_health_snapshot
order by component;
```

Bu üç alan mobil Dashboard'un ana veri kaynakları olacaktır.

---

# 39. Signal state kontrolü

```sql
select *
from model.signal_state
order by system;
```

Örnek:

```text
system             ETH/BTC
active_direction   BTC_TO_ETH
stage              1
cumulative_size    0.25
reset_counter      0
```

`model.signal_state` tablosunu production'da elle temizlemeyin.

---

# 40. Portföy işlemleri

Gelecekte mobil uygulamadaki:

- opening
- buy
- sell
- conversion
- exit
- cash in/out

işlemleri:

```text
public.portfolio_transactions
```

tablosuna yazılacaktır.

Kontrol:

```sql
select
  transaction_at,
  transaction_type,
  source_asset,
  target_asset,
  source_quantity,
  target_quantity,
  gross_usd,
  fee_usd,
  net_usd,
  platform,
  decision_id
from public.portfolio_transactions
order by transaction_at desc;
```

---

# 41. Mevcut pozisyon görünümü

```sql
select *
from public.portfolio_positions
order by user_id, account_id, asset;
```

---

# 42. Production güvenlik ayarları

## Supabase hesabı

Supabase hesabınızda MFA/2FA açın.

## Database SSL

Menü:

```text
Database
→ Settings
→ SSL Configuration
```

Engine:

```text
sslmode=require
```

kullanır.

## Network Restrictions

Menü:

```text
Database
→ Settings
→ Network Restrictions
```

Windows Server sabit public IP kullanıyorsa ileride yalnız bu IP'ye erişim verme değerlendirilebilir.

Dinamik IP'niz varsa yanlış restriction Engine bağlantısını kesebilir.

---

# 43. İlk kurulum sırası

```text
1. Supabase Project oluştur
2. Database Password'u kaydet
3. Connect → Session Pooler → View parameters aç
4. Host / Port / Database / User değerlerini not et
5. SQL Editor → 0001_schema.sql
6. SQL Editor → 0002_seed.sql
7. SQL Editor → 0003_mobile_api.sql
8. SQL Editor → 0004_v1_1_hardening.sql
9. SQL Editor → 0005_v1_1_2_macro_derivatives.sql
10. SQL Editor → 0006_v1_1_3_hardening_realtime_ura.sql
11. SQL kontrol sorgularını çalıştır
12. InvestmentEngine.exe aç
13. Supabase PostgreSQL bilgilerini gir
14. Supabase Test
15. Alpha Vantage / FRED / Global X / SEC / Telegram testlerini tamamla
16. Engine Mode = shadow; Realtime Execution = OFF
17. Windows Service'i kur/başlat
18. model.decisions ve public.engine_health_snapshot kontrol et
19. TEST_PLAN_V1_1_3.md smoke testini tamamla
20. Shadow doğrulaması tamamlanınca live moda geçişi ayrıca değerlendir
```

---

# 44. Doldurulacak bilgi formu

```text
SUPABASE PROJECT
----------------
Project Name:
Project Ref:

DATABASE
--------
Database Password:

SESSION POOLER
--------------
Host:
Port: 5432
Database: postgres
User:
SSL Mode: require

MOBILE — DAHA SONRA
-------------------
Project URL:
Publishable Key:

AUTH — DAHA SONRA
-----------------
Email Provider: Enabled
Confirm Email:
Site URL:
Redirect URL:
```

Database Password'u düz metin `.txt` dosyasında saklamayın.

Engine'e kaydedildikten sonra `settings` dosyası Windows DPAPI ile şifreli tutulur.

---

# 45. Kısa eşleştirme özeti

## Investment Engine

Menü:

```text
Supabase Dashboard
→ Connect
→ Session pooler
→ View parameters
```

| Supabase alanı | Engine alanı |
|---|---|
| Host | Host / Session Pooler |
| Port | Port |
| Database | Database |
| User | Kullanıcı |
| Database Password | DB Parolası |
| — | SSL Mode = require |

## Gelecekte Quasar Android uygulaması

Menü:

```text
Supabase Dashboard
→ Connect
```

veya:

```text
Settings
→ API Keys
```

| Supabase alanı | Mobil uygulama |
|---|---|
| Project URL | Supabase URL |
| Publishable Key | Supabase Publishable Key |

Mobil uygulamaya gitmeyecek bilgiler:

```text
Database Password
Secret Key
service_role
Telegram Bot Token
FRED API Key
Alpha Vantage API Key
```

---

# 46. Resmi Supabase referansları

Database bağlantısı:

```text
https://supabase.com/docs/guides/database/connecting-to-postgres
```

API keys:

```text
https://supabase.com/docs/guides/getting-started/api-keys
```

Auth:

```text
https://supabase.com/docs/guides/auth
```

Users:

```text
https://supabase.com/docs/guides/auth/users
```

Redirect URLs:

```text
https://supabase.com/docs/guides/auth/redirect-urls
```

Database overview:

```text
https://supabase.com/docs/guides/database/overview
```

Production checklist:

```text
https://supabase.com/docs/guides/deployment/going-into-prod
```

---

# 47. Son kontrol

Engine ayar ekranı şu biçimdeyse bağlantı tarafı doğrudur:

```text
Host / Session Pooler : aws-...pooler.supabase.com
Port                  : 5432
Database              : postgres
Kullanıcı              : postgres.PROJECT_REF
DB Parolası            : ********
SSL Mode               : require
```

**Supabase Test başarılı olmadan production/live moda geçmeyin.**

İlk kurulum:

```text
Engine Mode = shadow
```

olmalıdır.


# v1.1.2 ek migration

Mevcut v1.1.1 kurulumu için Supabase Dashboard:

```text
SQL Editor → New query
```

`migrations/0005_v1_1_2_macro_derivatives.sql` içeriğini yapıştırıp **Run** seçin. Bu migration OKX veri-kaynak metadata'sını ekler ve Deribit'i AUTO/fallback mimarisine göre günceller; tablo verilerini silmez.


# v1.1.3 ek migration

Mevcut v1.1.2 kurulumu için yalnız:

```text
SQL Editor → New query
→ migrations/0006_v1_1_3_hardening_realtime_ura.sql
→ Run
```

çalıştırılır. Migration:

- `fundamentals.ura_holdings.market_price` ekler,
- `market.execution_snapshots` tablosuna `ofi`, `trade_imbalance`, `trade_notional_usd`, `trade_gap_count`, `sample_window_seconds`, `test_run_id`, `is_test` ekler,
- test-run index'i oluşturur,
- `GLOBALX_URA_HOLDINGS` ve `COINBASE_REALTIME` data-source metadata'sını ekler.

Mevcut price/macro/decision verilerini silmez.

Kontrol:

```sql
select column_name
from information_schema.columns
where table_schema='market'
  and table_name='execution_snapshots'
  and column_name in ('ofi','trade_imbalance','trade_notional_usd','trade_gap_count','sample_window_seconds','test_run_id','is_test')
order by column_name;
```

Yeni kurulumda migration sırası:

```text
0001_schema.sql
0002_seed.sql
0003_mobile_api.sql
0004_v1_1_hardening.sql
0005_v1_1_2_macro_derivatives.sql
0006_v1_1_3_hardening_realtime_ura.sql
```

## v1.2.0 ek migration

v1.1.4 veya daha eski kurulumdan v1.2.0'a geçerken sıradaki migration:

```text
0007_v1_2_model_validation.sql
```

Bu migration `model.validation_runs`, `public.model_validation_snapshot` ve decision model-version provenance alanlarını ekler.
