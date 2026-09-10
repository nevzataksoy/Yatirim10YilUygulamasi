begin;

-- Post-Shadow P2.3 — macro.observations safe dedup + future transition storage.
--
-- Preconditions:
--   * deploy the hardened runtime first.  Its Repository.upsert_macro() is
--     compatible with both the legacy unique constraint and this schema.
--   * P2.3 production dry-run must have safe_dedup_contract_complete=true.
--
-- Contract:
--   * realtime_start/realtime_end changes alone are not economic revisions,
--   * keep the first row plus every value transition per series/date,
--   * delete only consecutive same-value current-view refetch rows,
--   * preserve A -> B -> A value reversions,
--   * allow multiple real value transitions on the same realtime_start date,
--   * fetched_at on newly inserted transition rows is first-seen provenance and
--     must not be refreshed by same-value refetches.
--
-- This migration does not change model thresholds, weights, signal state,
-- scheduler cadence, SHADOW/LIVE mode, or decision formulas.

-- Block concurrent macro writers while the validated transition cleanup and
-- legacy uniqueness removal happen in one transaction. Readers remain allowed.
lock table macro.observations in share row exclusive mode;

with ordered as (
    select
        o.id,
        o.value,
        row_number() over (
            partition by o.series_id, o.observation_date
            order by o.realtime_start asc, o.id asc
        ) as seq_no,
        lag(o.value) over (
            partition by o.series_id, o.observation_date
            order by o.realtime_start asc, o.id asc
        ) as previous_value
    from macro.observations o
),
candidates as (
    select id
    from ordered
    where seq_no > 1
      and value is not distinct from previous_value
)
delete from macro.observations o
using candidates c
where o.id = c.id;

-- The old constraint encoded query real-time date as version identity.  After
-- runtime hardening it would also prevent two genuine value transitions that
-- happen on the same calendar realtime_start date.
alter table macro.observations
  drop constraint if exists observations_series_id_observation_date_realtime_start_key;

-- Supports deterministic latest-version reads and the value-transition writer.
create index if not exists idx_macro_series_observation_version
  on macro.observations(
    series_id,
    observation_date desc,
    realtime_start desc,
    fetched_at desc,
    id desc
  );

comment on table macro.observations is
  'FRED current-view value-transition history; same-value refetch rows are not persisted.';
comment on column macro.observations.realtime_start is
  'FRED real-time date metadata; not by itself an economic revision identity.';
comment on column macro.observations.fetched_at is
  'First-seen timestamp for retained/current value-transition rows after P2.3 hardening.';

-- Transaction-local postcondition: no consecutive same-value row may remain
-- under the same ordering used by the validated P2.3 dry-run.
do $$
begin
    if exists (
        select 1
        from (
            select
                value,
                row_number() over (
                    partition by series_id, observation_date
                    order by realtime_start asc, fetched_at asc, id asc
                ) as seq_no,
                lag(value) over (
                    partition by series_id, observation_date
                    order by realtime_start asc, fetched_at asc, id asc
                ) as previous_value
            from macro.observations
        ) q
        where q.seq_no > 1
          and q.value is not distinct from q.previous_value
    ) then
        raise exception 'P2.3 macro cleanup postcondition failed: consecutive same-value rows remain';
    end if;
end $$;

commit;
