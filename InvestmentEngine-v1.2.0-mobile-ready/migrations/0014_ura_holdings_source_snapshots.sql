begin;

-- Post-Shadow P1 — immutable Global X URA holdings source snapshots.
--
-- Purpose:
--   * preserve every real issuer CSV fetch as an immutable raw source record,
--   * let future decisions reference the exact current/prior source snapshots,
--   * keep fundamentals.ura_holdings as the canonical/latest scoring surface.
--
-- Important:
--   * no UNIQUE constraint is placed on content_sha256: repeated fetches of the
--     same bytes are separate real fetch events and keep distinct fetched_at/id,
--   * this migration does not change factor formulas, thresholds, weights,
--     signal state, scheduler cadence, SHADOW/LIVE mode, or existing holdings.

create table if not exists fundamentals.ura_holdings_snapshots (
  id bigint generated always as identity primary key,
  holding_date date not null,
  source_url text not null,
  fetched_at timestamptz not null,
  content_sha256 text not null
    check (content_sha256 ~ '^[0-9a-f]{64}$'),
  raw_csv bytea not null
    check (octet_length(raw_csv) > 0),
  constituent_count integer not null
    check (constituent_count > 0),
  created_at timestamptz not null default now()
);

create index if not exists idx_ura_holdings_snapshots_date_fetch
  on fundamentals.ura_holdings_snapshots(holding_date, fetched_at desc, id desc);

create index if not exists idx_ura_holdings_snapshots_sha256
  on fundamentals.ura_holdings_snapshots(content_sha256);

comment on table fundamentals.ura_holdings_snapshots is
  'Immutable raw Global X URA full-holdings CSV fetch history for source-level audit/replay.';
comment on column fundamentals.ura_holdings_snapshots.content_sha256 is
  'SHA-256 of exact HTTP response bytes stored in raw_csv.';

commit;
