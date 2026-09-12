from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "0015_macro_observations_transition_dedup.sql"
SUPABASE_MIGRATION = ROOT / "supabase-migrations" / "0015_macro_observations_transition_dedup.sql"


def test_macro_transition_dedup_migration_is_mirrored() -> None:
    assert MIGRATION.read_text(encoding="utf-8") == SUPABASE_MIGRATION.read_text(encoding="utf-8")


def test_macro_transition_dedup_migration_preserves_revision_contract() -> None:
    sql = " ".join(MIGRATION.read_text(encoding="utf-8").lower().split())

    assert "lock table macro.observations in share row exclusive mode" in sql
    assert "lag(o.value) over" in sql
    assert "value is not distinct from previous_value" in sql
    assert "delete from macro.observations" in sql
    assert "drop constraint if exists observations_series_id_observation_date_realtime_start_key" in sql
    assert "create index if not exists idx_macro_series_observation_version" in sql
    assert "raise exception 'p2.3 macro cleanup postcondition failed" in sql

    # P2.3 is a storage/read-contract hardening only; it must not tune the model.
    forbidden = (
        "edge_threshold",
        "confidence_threshold",
        "recommended_size",
        "reset_days",
        "engine_mode",
    )
    assert not any(token in sql for token in forbidden)
