from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

from .path import path_in_data, ensure_dir

SCENARIO_MAP = {
    # Harmonise FES25 -> FES24 naming
    "Falling Behind": "Counterfactual",

    # (optional) add other known equivalences if they exist in your files
    # "Leading the Way": "Leading The Way",
    # "System Transformation": "System Transformation",
    # "Consumer Transformation": "Consumer Transformation",
}

def get_stock_columns(df: pd.DataFrame, include_totals: bool = True) -> List[str]:
    """Stock columns: 'stock ...' excluding 'stock_proportion...'."""
    stock_cols = [c for c in df.columns if c.startswith("stock ") and not c.startswith("stock_proportion")]
    if not include_totals:
        stock_cols = [c for c in stock_cols if c not in ["stock Total", "stock TotalHPs"]]
    return stock_cols


def to_long_stock(df: pd.DataFrame, id_cols: List[str], stock_cols: List[str]) -> pd.DataFrame:
    """Wide -> long: id_cols + Technology + Stock."""
    out = df[id_cols + stock_cols].copy()
    for c in stock_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    long_df = out.melt(
        id_vars=id_cols,
        value_vars=stock_cols,
        var_name="Technology",
        value_name="Stock",
    )
    long_df["Technology"] = long_df["Technology"].str.replace("stock ", "", regex=False)
    long_df["Technology"] = long_df["Technology"].str.strip()

    return long_df


def read_snapshot_file(path: Path, include_totals: bool = True) -> pd.DataFrame:
    """Read one LA snapshot CSV and return long format with LA_Code/LA name/Scenario/Year/Technology/Stock."""
    df = pd.read_csv(path)

    # --- Standardise column names (case-insensitive + known variants) ---
    cols_lower = {c.lower(): c for c in df.columns}
    rename_map = {}

    # LA code variants: CODE_x / la_code / LA_CODE / etc.
    if "code_x" in cols_lower:
        rename_map[cols_lower["code_x"]] = "LA_Code"
    elif "la_code" in cols_lower:
        rename_map[cols_lower["la_code"]] = "LA_Code"

    # Scenario variants: Scenario / Pathway (your 2024/2025)
    if "scenario" in cols_lower:
        rename_map[cols_lower["scenario"]] = "Scenario"
    elif "pathway" in cols_lower:
        rename_map[cols_lower["pathway"]] = "Scenario"

    # Local authority name variants (keep robust)
    if "local_authority" in cols_lower:
        rename_map[cols_lower["local_authority"]] = "Local_Authority"
    elif "local authority" in cols_lower:
        rename_map[cols_lower["local authority"]] = "Local_Authority"

    # Year variants (usually stable, but keep robust)
    if "year" in cols_lower:
        rename_map[cols_lower["year"]] = "Year"

    if rename_map:
        df = df.rename(columns=rename_map)
    # ---- Normalise merge keys ----
    df["LA_Code"] = df["LA_Code"].astype(str).str.strip().str.upper()

    df["Scenario"] = df["Scenario"].astype(str).str.strip()
    df["Scenario"] = df["Scenario"].replace(SCENARIO_MAP)

    df["Local_Authority"] = df["Local_Authority"].astype(str).str.strip()


    # --- Validate required columns ---
    required = ["LA_Code", "Local_Authority", "Scenario", "Year"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{path.name}: missing required columns {missing}. "
            f"Available columns: {df.columns.tolist()}"
        )

    stock_cols = get_stock_columns(df, include_totals=include_totals)

    return to_long_stock(
        df,
        id_cols=["LA_Code", "Local_Authority", "Scenario", "Year"],
        stock_cols=stock_cols,
    )



def _release_prefix(fes_release_year: int) -> str:
    """
    Convert 2021 -> 'fes21', 2024 -> 'fes24'.
    Assumes your naming convention uses 2-digit release year.
    """
    return f"fes{str(fes_release_year)[-2:]}"

def _load_base_table_from_release(
    fes_release_year: int,
    base_year: int,
    include_totals: bool,
    folder_name: str,
    pattern: Optional[str],
) -> pd.DataFrame:
    """
    Load ONLY the base-year table (long->base wide metadata) from a given release folder.
    Returns base table with columns:
      LA_Code | Local_Authority | Scenario | BaseYear | Technology | BaseStock
    """
    fes_dir = Path(path_in_data(folder_name, str(fes_release_year)))
    if not fes_dir.exists():
        raise FileNotFoundError(f"Folder not found: {fes_dir}")

    snapshot_files = _find_snapshot_files(fes_dir, fes_release_year, pattern=pattern)
    if not snapshot_files:
        raise FileNotFoundError(f"No snapshot files found in {fes_dir}")

    all_long = pd.concat(
        [read_snapshot_file(f, include_totals=include_totals) for f in snapshot_files],
        ignore_index=True,
    )
    all_long["Year"] = all_long["Year"].astype(int)

    base = all_long[all_long["Year"] == base_year].copy()
    if base.empty:
        raise ValueError(f"Base year {base_year} not present in release {fes_release_year}")

    base = base.rename(columns={"Year": "BaseYear", "Stock": "BaseStock"})[
        ["LA_Code", "Local_Authority", "Scenario", "BaseYear", "Technology", "BaseStock"]
    ]
    return base

def _find_snapshot_files(
    fes_dir: Path,
    fes_release_year: int,
    pattern: Optional[str] = None,
) -> List[Path]:
    """
    Find snapshot files for one release folder using the new naming convention:
      fesYY_la_level_outputs_YYYY_residential_all_scenarios.csv

    If pattern is provided, it is used as-is.
    Otherwise, a release-specific pattern is constructed.
    """
    if pattern is None:
        prefix = _release_prefix(fes_release_year)
        pattern = f"{prefix}_la_level_outputs_*_residential_all_scenarios.csv"

    files = sorted(fes_dir.glob(pattern))

    # Optional fallback (useful if you later rename 'residential' or tweak suffix)
    if not files and pattern is None:
        files = sorted(fes_dir.glob("fes*_la_level_outputs_*_residential_all_scenarios.csv"))

    return files


def build_wide_scaling_table_for_fes_release(
    fes_release_year: int,
    base_year: int = 2020,
    include_totals: bool = True,
    epsilon: float = 0.0,
    folder_name: str = "FES_Spatial_Heat_Model",
    pattern: Optional[str] = None,
    verbose: bool = True,
    base_override: Optional[pd.DataFrame] = None,  # <-- add this
) -> pd.DataFrame:

    """
    Build a WIDE scaling-factor table for one FES release folder.

    Output schema:
      LA_Code | Local_Authority | Scenario | BaseYear | Technology | BaseStock | SF_2025 | SF_2030 | ...

    Notes:
    - Snapshot files are discovered from filenames in the folder using the NEW naming scheme.
    - BaseStock is taken from rows where Year == base_year.
    - If BaseStock == 0 and epsilon == 0 -> SF is NaN (recommended).
    """
    fes_dir = Path(path_in_data(folder_name, str(fes_release_year)))
    if not fes_dir.exists():
        raise FileNotFoundError(f"Folder not found: {fes_dir}")

    snapshot_files = _find_snapshot_files(fes_dir, fes_release_year, pattern=pattern)
    if not snapshot_files:
        raise FileNotFoundError(
            f"No snapshot files found in {fes_dir} for release {fes_release_year}. "
            f"Expected pattern like: {_release_prefix(fes_release_year)}_la_level_outputs_*_residential_all_scenarios.csv"
        )

    if verbose:
        print(f"\nFES release {fes_release_year} ({fes_dir})")
        print(f"Found {len(snapshot_files)} files:")
        for f in snapshot_files:
            print(f"  - {f.name}")

    # Read all snapshots into one long table
    all_long = pd.concat(
        [read_snapshot_file(f, include_totals=include_totals) for f in snapshot_files],
        ignore_index=True,
    )

    # Ensure Year is int
    all_long["Year"] = all_long["Year"].astype(int)

    # ---- Base table ----
    if base_override is not None:
        base = base_override.copy()
    else:
        base = all_long[all_long["Year"] == base_year].copy()
        if base.empty:
            available_years = sorted(all_long["Year"].unique().tolist())
            raise ValueError(
                f"Base year {base_year} not found in {fes_dir}. Available years: {available_years}"
            )

        base = base.rename(columns={"Year": "BaseYear", "Stock": "BaseStock"})[
            ["LA_Code", "Local_Authority", "Scenario", "BaseYear", "Technology", "BaseStock"]
        ]


    base = base.rename(columns={"Year": "BaseYear", "Stock": "BaseStock"})[
        ["LA_Code", "Local_Authority", "Scenario", "BaseYear", "Technology", "BaseStock"]
    ]

    # ---- Compute SF for every snapshot year ----
    merged = all_long.merge(
        base[["LA_Code", "Scenario", "Technology", "BaseStock", "BaseYear"]],
        on=["LA_Code", "Scenario", "Technology"],
        how="left",
        validate="m:1",
    )

    denom = merged["BaseStock"].astype(float)
    if epsilon > 0:
        denom = denom.clip(lower=epsilon)
        merged["SF"] = merged["Stock"] / denom
    else:
        merged["SF"] = np.where(denom > 0, merged["Stock"] / denom, np.nan)

    # Keep only non-base years for SF columns
    sf_long = merged[merged["Year"] != base_year].copy()
    sf_long["SF_Col"] = "SF_" + sf_long["Year"].astype(str)

    # Pivot SF into wide columns
    sf_wide = sf_long.pivot_table(
        index=["LA_Code", "Scenario", "Technology"],
        columns="SF_Col",
        values="SF",
        aggfunc="first",
    ).reset_index()

    # Add Local_Authority + BaseYear + BaseStock back (base LA name is safest)
    out = base.merge(
        sf_wide,
        on=["LA_Code", "Scenario", "Technology"],
        how="left",
        validate="1:1",
    )

    # Column ordering: metadata then SF_* columns sorted by year
    sf_cols = sorted([c for c in out.columns if c.startswith("SF_")], key=lambda x: int(x.split("_")[1]))
    out = out[["LA_Code", "Local_Authority", "Scenario", "BaseYear", "Technology", "BaseStock"] + sf_cols]

    return out


def build_scaling_tables_for_multiple_releases(
    fes_release_years: List[int],
    base_year: int = 2020,
    include_totals: bool = True,
    epsilon: float = 0.0,
    folder_name: str = "FES_Spatial_Heat_Model",
    verbose: bool = True,
    skip_missing: bool = True,  # <-- best practice for batch runs
) -> Dict[int, Path]:
    """
    Loop through multiple FES release folders and save one scaling table per folder.
    Returns dict {release_year: output_path}.
    """
    outputs: Dict[int, Path] = {}

    # Ensure releases are processed in ascending order so "previous release" is well-defined
    fes_release_years_sorted = sorted(fes_release_years)

    for y in fes_release_years_sorted:
        try:
            df = build_wide_scaling_table_for_fes_release(
                fes_release_year=y,
                base_year=base_year,
                include_totals=include_totals,
                epsilon=epsilon,
                folder_name=folder_name,
                pattern=None,
                verbose=verbose,
                base_override=None,
            )
        except ValueError as e:
            # If base year is missing in this release, fall back to nearest previous release that has it
            msg = str(e)
            if "Base year" in msg and "not found" in msg:
                prev_releases = [r for r in fes_release_years_sorted if r < y]
                base_tbl = None

                # search backwards: y-1 release, y-2 release, ...
                for r in reversed(prev_releases):
                    try:
                        base_tbl = _load_base_table_from_release(
                            fes_release_year=r,
                            base_year=base_year,
                            include_totals=include_totals,
                            folder_name=folder_name,
                            pattern=None,
                        )
                        if verbose:
                            print(f"Release {y}: base {base_year} missing; using base from release {r} instead.")
                        break
                    except (FileNotFoundError, ValueError):
                        continue

                if base_tbl is None:
                    if skip_missing:
                        print(f"\nSkipping {y}: no previous release contains base year {base_year}.")
                        continue
                    raise ValueError(f"Release {y}: no previous release contains base year {base_year}.") from e

                # now rebuild df for y using the external base table
                df = build_wide_scaling_table_for_fes_release(
                    fes_release_year=y,
                    base_year=base_year,
                    include_totals=include_totals,
                    epsilon=epsilon,
                    folder_name=folder_name,
                    pattern=None,
                    verbose=verbose,
                    base_override=base_tbl,
                )
            else:
                if skip_missing:
                    print(f"\nSkipping {y}: {e}")
                    continue
                raise
        except FileNotFoundError as e:
            if skip_missing:
                print(f"\nSkipping {y}: {e}")
                continue
            raise

        out_path = Path(path_in_data(folder_name, str(y), f"LA_tech_stock_scaling_factors_FES_{y}.csv"))
        ensure_dir(out_path.parent)
        df.to_csv(out_path, index=False)
        outputs[y] = out_path

        if verbose:
            print(f"Saved {y}: {out_path}")


    return outputs


if __name__ == "__main__":
    # Choose which FES release folders to process
    fes_release_years = [2021, 2022, 2024, 2025]

    outputs = build_scaling_tables_for_multiple_releases(
        fes_release_years=fes_release_years,
        base_year=2020,
        include_totals=True,
        epsilon=0.0,  # NaN when base tech stock is zero (recommended)
        folder_name="FES_Spatial_Heat_Model",
        verbose=True,
        skip_missing=True,
    )

    for y, p in outputs.items():
        print(f"Final output {y}: {p}")
