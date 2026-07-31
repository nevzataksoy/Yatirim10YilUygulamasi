begin;

-- v1.1.2: derivatives provider fallback metadata.  No table shape change is
-- required because market.derivatives_snapshots already stores venue.
update system.data_sources
set required=false,
    notes='AUTO modunda birincil derivatives provider; erişilemezse OKX fallback'
where code='DERIBIT';

insert into system.data_sources
(code,category,source_url,expected_interval_seconds,stale_after_seconds,required,enabled,notes)
values
('OKX','derivatives','https://www.okx.com/api/v5',3600,10800,false,true,
 'Deribit erişilemezse BTC/ETH aynı venue olacak şekilde public OI/funding/mark/index fallback')
on conflict(code) do update set
  category=excluded.category,
  source_url=excluded.source_url,
  expected_interval_seconds=excluded.expected_interval_seconds,
  stale_after_seconds=excluded.stale_after_seconds,
  required=excluded.required,
  enabled=excluded.enabled,
  notes=excluded.notes;

update system.data_sources
set notes='Son observation DESC çekilir; decision katmanı seri bazında observation-date freshness uygular'
where code='FRED';

commit;
