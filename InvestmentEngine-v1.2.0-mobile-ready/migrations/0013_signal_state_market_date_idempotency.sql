begin;

-- Post-Shadow P1 production/replay hardening.
--
-- Problem:
--   Production may persist more than one decision for the same system + market
--   as_of when supporting inputs settle after the close. reset_counter is a
--   market-day/state rule, so repeated evaluation of the same market date must
--   not count as another reset day.
--
-- Scope:
--   - persist the latest market as_of that reached signal-state evaluation,
--   - backfill it from the latest existing decision per system,
--   - keep it synchronized after each future decision insert.
--
-- This migration does NOT change thresholds, weights, K1/K2 sizing, reversal
-- semantics, scheduler cadence, SHADOW/LIVE mode, or decision history retention.

alter table model.signal_state
  add column if not exists last_evaluated_as_of date;

update model.signal_state s
set last_evaluated_as_of = (
  select d.as_of
  from model.decisions d
  where d.system = s.system
  order by d.created_at desc, d.id desc
  limit 1
)
where s.last_evaluated_as_of is null;

create or replace function model.sync_signal_state_last_evaluated_as_of()
returns trigger
language plpgsql
as $$
begin
  update model.signal_state
  set last_evaluated_as_of = new.as_of
  where system = new.system;
  return new;
end;
$$;

drop trigger if exists trg_signal_state_last_evaluated_as_of on model.decisions;
create trigger trg_signal_state_last_evaluated_as_of
after insert on model.decisions
for each row
execute function model.sync_signal_state_last_evaluated_as_of();

commit;
