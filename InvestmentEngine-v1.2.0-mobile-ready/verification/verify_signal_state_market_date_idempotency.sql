-- Read-only verification for migration 0013_signal_state_market_date_idempotency.sql.
-- No writes, DDL, settings, thresholds, state transitions, or scheduler changes.

with column_check as (
  select exists (
    select 1
    from information_schema.columns
    where table_schema = 'model'
      and table_name = 'signal_state'
      and column_name = 'last_evaluated_as_of'
      and data_type = 'date'
  ) as present
),
trigger_check as (
  select jsonb_build_object(
    'present', count(*) = 1,
    'enabled', coalesce(bool_and(t.tgenabled <> 'D'), false),
    'trigger_name', max(t.tgname),
    'function_name', max(p.proname)
  ) as result
  from pg_trigger t
  join pg_class c on c.oid = t.tgrelid
  join pg_namespace n on n.oid = c.relnamespace
  join pg_proc p on p.oid = t.tgfoid
  where not t.tgisinternal
    and n.nspname = 'model'
    and c.relname = 'decisions'
    and t.tgname = 'trg_signal_state_last_evaluated_as_of'
),
latest_decision as (
  select distinct on (d.system)
    d.system,
    d.as_of,
    d.id,
    d.created_at
  from model.decisions d
  order by d.system, d.created_at desc, d.id desc
),
state_rows as (
  select
    s.system,
    s.active_direction,
    s.stage,
    s.cumulative_size,
    s.last_action_date,
    s.reset_counter,
    s.last_evaluated_as_of,
    ld.as_of as latest_decision_as_of,
    ld.id as latest_decision_id,
    ld.created_at as latest_decision_created_at,
    (s.last_evaluated_as_of is not distinct from ld.as_of) as matches_latest_decision
  from model.signal_state s
  left join latest_decision ld on ld.system = s.system
),
state_summary as (
  select jsonb_build_object(
    'signal_state_rows', count(*),
    'rows_with_last_evaluated_as_of', count(*) filter (where last_evaluated_as_of is not null),
    'rows_matching_latest_decision_as_of', count(*) filter (where matches_latest_decision),
    'rows_not_matching_latest_decision_as_of', count(*) filter (where not matches_latest_decision),
    'rows_without_latest_decision', count(*) filter (where latest_decision_id is null)
  ) as result
  from state_rows
)
select jsonb_build_object(
  'signal_state_market_date_idempotency', jsonb_build_object(
    'column_present', (select present from column_check),
    'trigger', (select result from trigger_check),
    'state_summary', (select result from state_summary),
    'state_rows', coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'system', system,
          'active_direction', active_direction,
          'stage', stage,
          'cumulative_size', cumulative_size,
          'last_action_date', last_action_date,
          'reset_counter', reset_counter,
          'last_evaluated_as_of', last_evaluated_as_of,
          'latest_decision_as_of', latest_decision_as_of,
          'latest_decision_id', latest_decision_id,
          'latest_decision_created_at', latest_decision_created_at,
          'matches_latest_decision', matches_latest_decision
        )
        order by system
      )
      from state_rows
    ), '[]'::jsonb)
  )
) as signal_state_market_date_idempotency;
