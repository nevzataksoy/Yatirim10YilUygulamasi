# Backup / Restore

## Supabase

Asıl kalıcı veri Supabase PostgreSQL'dedir. Supabase planınızın sağladığı backup özelliklerine ek olarak kritik kullanıcı transaction tablolarını düzenli dışa aktarın.

Öncelikli tablolar:

- `public.profiles`
- `public.investment_accounts`
- `public.portfolio_transactions`
- `public.user_investment_settings`

Engine market/model verileri tekrar toplanabilir fakat backtest/audit sürekliliği için ayrıca yedeklenmesi önerilir.

## Windows

`settings` ve `rosalock` yalnız aynı Windows makinede DPAPI ile açılabilir. Başka sunucuya restore planı **dosyaları kopyalamak değil, ayarları yeni makinede tekrar girmektir**.

`runtime\spool.db` kısa süreli retry kuyruğudur; source of truth değildir.
