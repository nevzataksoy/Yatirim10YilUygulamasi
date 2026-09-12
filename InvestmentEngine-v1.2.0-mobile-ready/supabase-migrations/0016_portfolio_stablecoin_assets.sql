begin;

-- Quasar portfolio domain expansion only.
-- The running Python Investment Engine does not read/write public.portfolio_transactions;
-- service-owned market/model/system tables are intentionally untouched.
alter table public.portfolio_transactions
  drop constraint if exists portfolio_transactions_price_currency_check;

alter table public.portfolio_transactions
  add constraint portfolio_transactions_price_currency_check
  check (price_currency is null or price_currency in ('USD','TRY','USDT','USDC'));

comment on column public.portfolio_transactions.price_currency is
  'Transaction-entered settlement currency. Supported: USD, TRY, USDT, USDC.';

commit;
