from __future__ import annotations

import json


def build_feature_rows(system: str, as_of: str, features: dict[str, dict]) -> list[tuple]:
    """Convert feature payloads into rows accepted by model.features.

    Builders may include non-numeric metadata (currently ``as_of``). The DB
    column ``value`` is numeric, therefore metadata/non-numeric values are
    deliberately omitted from persistence while remaining available to the
    in-memory decision engine.
    """
    rows: list[tuple] = []
    for code, data in features.items():
        if code == "as_of":
            continue
        raw_value = data.get("value")
        if raw_value is None:
            value = None
        else:
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
        raw_z = data.get("z_score")
        z_score = None if raw_z is None else float(raw_z)
        quality = float(data.get("quality", 100))
        rows.append((
            as_of,
            system,
            code,
            value,
            z_score,
            quality,
            json.dumps(data.get("details", {})),
        ))
    return rows
