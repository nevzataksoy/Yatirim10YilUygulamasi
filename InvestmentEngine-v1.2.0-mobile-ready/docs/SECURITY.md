# Güvenlik

## Windows

- EXE ayar işlemleri UAC/admin ister.
- settings/rosalock EXE klasöründedir ve DPAPI LocalMachine ile şifrelenmiştir.
- rosalock ayar parolasının kendisini içermez.
- dosya DACL'i LocalSystem + Administrators ile sınırlandırılır.
- Windows Service LocalSystem altında çalışır; dışarıya inbound port açılması gerekmez.

## Supabase

- Engine PostgreSQL parolası yalnız settings içindedir.
- Mobil uygulama yalnız public/publishable key kullanır.
- service-role key istemciye konmaz.
- kullanıcı verileri RLS ile `auth.uid()` üzerinden ayrılır.
- engine-private şemalar mobil API yüzeyinin dışında tutulur.

## API sırları

Telegram token, FRED ve Alpha Vantage key'leri loglara yazılmamalıdır. Hata mesajlarında HTTP URL içine key gömülmemesi collector tasarımının parçasıdır; yine de production loglarını düzenli denetleyin.
