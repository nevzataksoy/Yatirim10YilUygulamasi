-- Post-Shadow P1 — URA immutable raw source snapshot forward verification.
-- READ-ONLY. Run after migration 0014 + hardened runtime deployment + a natural
-- daily_ura_job decision. It does not mutate model state, snapshots or settings.

with latest_decision as (
    select
        d.id,
        d.created_at,
        d.as_of,
        d.status,
        d.factors,
        d.rationale
    from model.decisions d
    where d.system='URA/USD'
      and d.model_version='1.2.0'
    order by d.created_at desc,d.id desc
    limit 1
), refs as (
    select
        d.*,
        d.factors #> '{fundamentals,details,source_snapshots,current}' as current_ref,
        d.factors #> '{fundamentals,details,source_snapshots,previous}' as previous_ref
    from latest_decision d
), resolved as (
    select
        r.*,
        cur.id as current_snapshot_id,
        cur.holding_date as current_holding_date,
        cur.fetched_at as current_fetched_at,
        cur.content_sha256 as current_sha256,
        octet_length(cur.raw_csv) as current_raw_size_bytes,
        encode(digest(cur.raw_csv,'sha256'),'hex') as current_recomputed_sha256,
        prev.id as previous_snapshot_id,
        prev.holding_date as previous_holding_date,
        prev.fetched_at as previous_fetched_at,
        prev.content_sha256 as previous_sha256,
        octet_length(prev.raw_csv) as previous_raw_size_bytes,
        encode(digest(prev.raw_csv,'sha256'),'hex') as previous_recomputed_sha256
    from refs r
    left join fundamentals.ura_holdings_snapshots cur
      on cur.id=(r.current_ref->>'id')::bigint
    left join fundamentals.ura_holdings_snapshots prev
      on prev.id=(r.previous_ref->>'id')::bigint
)
select jsonb_build_object(
    'latest_decision', jsonb_build_object(
        'id', id,
        'created_at', created_at,
        'as_of', as_of,
        'status', status,
        'decision_evaluated_at', rationale #>> '{provenance,decision_evaluated_at}'
    ),
    'current', jsonb_build_object(
        'ref_present', jsonb_typeof(current_ref)='object',
        'snapshot_id', current_snapshot_id,
        'holding_date', current_holding_date,
        'fetched_at', current_fetched_at,
        'raw_size_bytes', current_raw_size_bytes,
        'ref_id_matches', current_snapshot_id=(current_ref->>'id')::bigint,
        'ref_date_matches', current_holding_date::text=current_ref->>'holding_date',
        'ref_sha_matches', current_sha256=current_ref->>'content_sha256',
        'raw_sha_valid', current_sha256=current_recomputed_sha256,
        'raw_present', coalesce(current_raw_size_bytes,0)>0
    ),
    'previous', jsonb_build_object(
        'ref_present', jsonb_typeof(previous_ref)='object',
        'snapshot_id', previous_snapshot_id,
        'holding_date', previous_holding_date,
        'fetched_at', previous_fetched_at,
        'raw_size_bytes', previous_raw_size_bytes,
        'ref_id_matches', previous_snapshot_id=(previous_ref->>'id')::bigint,
        'ref_date_matches', previous_holding_date::text=previous_ref->>'holding_date',
        'ref_sha_matches', previous_sha256=previous_ref->>'content_sha256',
        'raw_sha_valid', previous_sha256=previous_recomputed_sha256,
        'raw_present', coalesce(previous_raw_size_bytes,0)>0
    ),
    'forward_contract_complete',
        jsonb_typeof(current_ref)='object'
        and current_snapshot_id is not null
        and current_snapshot_id=(current_ref->>'id')::bigint
        and current_holding_date::text=current_ref->>'holding_date'
        and current_sha256=current_ref->>'content_sha256'
        and current_sha256=current_recomputed_sha256
        and coalesce(current_raw_size_bytes,0)>0
        and (
            previous_ref is null
            or previous_ref='null'::jsonb
            or (
                jsonb_typeof(previous_ref)='object'
                and previous_snapshot_id is not null
                and previous_snapshot_id=(previous_ref->>'id')::bigint
                and previous_holding_date::text=previous_ref->>'holding_date'
                and previous_sha256=previous_ref->>'content_sha256'
                and previous_sha256=previous_recomputed_sha256
                and coalesce(previous_raw_size_bytes,0)>0
            )
        )
) as ura_holdings_source_snapshot_forward
from resolved;
