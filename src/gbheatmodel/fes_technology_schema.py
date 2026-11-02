"""NESO FES hybrid-column rename compatibility (announcement: 28 October 2026).

The default GBHeat representation retains legacy internal names so existing
technology-specific demand and electricity calculations do not change.
Raw source names, including the new NESO names, are accepted at the boundary.
Do not conflate Biofuel (2024) with BioLPG (2025).
"""
from __future__ import annotations

import pandas as pd

NESO_SOURCE = "https://www.neso.energy/data-portal/local-authority-level-spatial-heat-model-outputs-fes"

# Only grammatical header updates specified by NESO. These are exact label
# aliases, not changes of heating technology or technology-stock quantities.
HYBRID_LABELS = {
    "Hybrid (ASHP + Biofuel boiler)": "Hybrid ASHP and Biofuel boiler",
    "Hybrid (ASHP + BioLPG boiler)": "Hybrid ASHP and BioLPG boiler",
    "Hybrid (ASHP + Hydrogen boiler)": "Hybrid ASHP and Hydrogen boiler",
    "Hybrid (ASHP + Electric resistive)": "Hybrid ASHP and Electric resistive",
}
# Historical NESO files may contain a mixture of old and new labels.
# Use the established GBHeat labels internally, until all downstream consumers
# (including electric_demand.py) are migrated together.
TO_GBHEAT = {new: old for old, new in HYBRID_LABELS.items()}


def harmonise_fes_headers(df: pd.DataFrame, *, target: str = "gbheat") -> pd.DataFrame:
    """Standardise `stock ` and `stock_proportion ` hybrid column headers.

    `target='gbheat'` retains the model's established names (default).
    `target='neso'` uses the October 2026 official NESO source names.
    Non-hybrid and metadata columns are passed through unchanged.

    Raises instead of silently overwriting if both aliases are present.
    """
    if target not in ("gbheat", "neso"):
        raise ValueError("target must be 'gbheat' or 'neso'")
    aliases = TO_GBHEAT if target == "gbheat" else HYBRID_LABELS
    rename = {}
    for col in df.columns:
        for prefix in ("stock ", "stock_proportion "):
            if col.startswith(prefix):
                label = col[len(prefix):]
                if label in aliases:
                    rename[col] = prefix + aliases[label]
                break
    final_columns = [rename.get(col,col) for col in df.columns]
    if len(final_columns) != len(set(final_columns)):
        collisions = sorted({x for x in final_columns if final_columns.count(x) > 1})
        raise ValueError(f"Both old and new FES technology headers occur: {collisions}. Resolve duplicates explicitly.")
    return df.rename(columns=rename).copy()


def harmonise_grid_technology_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert bare NESO hybrid headings to existing GBHeat technology labels.

    The grid-stage tables no longer contain the `stock ` prefix.
    """
    rename = {col: TO_GBHEAT[col] for col in df if col in TO_GBHEAT}
    out = [rename.get(c,c) for c in df.columns]
    if len(out) != len(set(out)):
        raise ValueError("Conflicting old/new grid hybrid technology columns")
    return df.rename(columns=rename).copy()
