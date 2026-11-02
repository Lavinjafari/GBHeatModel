"""Annual domestic heating-demand scaling relative to FES historic 2020.

Preserves GBHeat's existing scalar definition:
    projected annual residential heat demand / FES historical 2020 demand.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

from .path import path_in_data
from .FES_heat_supply_data import _vintage, resolve_FES_scenario


def FES_scaling_factor_calc(future_year, FES, scenario, *, data_dir=None) -> float:
    """Return dimensionless heating demand scaling for a year/pathway/vintage.

    `data_dir` optionally overrides the specific FES vintage directory, useful
    for tests. Reject unknown vintage, pathway, year, and missing numeric values.
    """
    vintage = _vintage(FES)
    _, full_name = resolve_FES_scenario(vintage, scenario)
    base = Path(data_dir) if data_dir is not None else path_in_data("FES_Spatial_Heat_Model", vintage)
    path = base / f"Annual Heat Demand - FES{vintage[-2:]}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Missing FES annual residential heat-demand table: {path}")
    df = pd.read_csv(path, index_col=0)
    # Recent FES CSVs have trailing provenance text and sometimes spaces in
    # names; use exact stripped scenario labels, not partial text matching.
    df.index = df.index.map(lambda x: str(x).strip())
    df.columns = df.columns.map(str)
    target = str(int(future_year))
    if target not in df.columns:
        raise ValueError(f"FES {vintage} annual-demand table has no year {target}")
    if full_name not in df.index:
        raise ValueError(f"FES {vintage} annual-demand table has no pathway {full_name!r}")
    if "History" not in df.index or "2020" not in df.columns:
        raise ValueError(f"FES {vintage} annual-demand table has no historic 2020 reference")
    future = pd.to_numeric(pd.Series([df.loc[full_name, target]]), errors="coerce").iloc[0]
    historical = pd.to_numeric(pd.Series([df.loc["History", "2020"]]), errors="coerce").iloc[0]
    if pd.isna(future) or pd.isna(historical) or historical <= 0 or future < 0:
        raise ValueError(f"Missing/invalid demand value for FES {vintage}, {full_name}, {target}")
    return float(future / historical)
