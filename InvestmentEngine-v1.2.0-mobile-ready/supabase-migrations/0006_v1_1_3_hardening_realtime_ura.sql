begin;

-- v1.1.3: realtime observability + URA official holdings history.

alter table fundamentals.ura_holdings
  add column if not exists market_price numeric(28,10);

alter table market.execution_snapshots
  add column if not exists ofi numeric(18,8),
  add column if not exists trade_imbalance numeric(18,8),
  add column if not exists trade_notional_usd numeric(28,4),
  add column if not exists trade_gap_count integer not null default 0,
  add column if not exists sample_window_seconds integer,
  add column if not exists test_run_id uuid,
  add column if not exists is_test boolean not null default false;

create index if not exists idx_execution_test_run on market.execution_snapshots(test_run_id, observed_at)
where test_run_id is not null;

insert into system.data_sources
(code,category,source_url,expected_interval_seconds,stale_after_seconds,required,enabled,notes)
values
('GLOBALX_URA_HOLDINGS','fundamentals','https://www.globalxetfs.com/funds/ura',86400,259200,false,true,
 'Global X URA resmi Full Holdings CSV; dated CSV URL fund sayfasından keşfedilir.'),
('COINBASE_REALTIME','execution','wss://ws-feed.exchange.coinbase.com',0,0,false,true,
 'Public level2_batch + matches realtime execution gözlemi; otomatik emir göndermez.')
on conflict(code) do update set
  category=excluded.category,
  source_url=excluded.source_url,
  expected_interval_seconds=excluded.expected_interval_seconds,
  stale_after_seconds=excluded.stale_after_seconds,
  required=excluded.required,
  enabled=excluded.enabled,
  notes=excluded.notes;

commit;
