# Supabase Auth ve RLS Güvenlik Modeli

- Mobil istemci yalnız public/publishable key kullanır.
- Kullanıcı kimliği Supabase Auth JWT içindeki `auth.uid()` üzerinden gelir.
- `profiles`, `investment_accounts`, `portfolio_transactions`, `user_investment_settings` RLS açıktır.
- Portföy kayıtları `user_id = auth.uid()` olmadan okunamaz/yazılamaz.
- Engine market/model şemaları mobil istemciye açılmaz.
- `decision_snapshot` ve `engine_health_snapshot` yalnız authenticated SELECT verir.
- `anon` role engine karar/health ve kullanıcı tablolarında izin verilmez.
- Service-role key mobil uygulamaya eklenmemelidir.
