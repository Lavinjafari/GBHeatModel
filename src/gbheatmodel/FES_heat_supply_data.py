"""Read and validate GBHeat FES LA-level heating technology stocks (2021–2025).

Public APIs retained: read_FES_heat_supply(FES), year_FES_heat_supply(year,FES,scenario).
All years use the FES *spatial* outputs; target years between available stock years
select the latest published stock year not greater than the target year.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .path import path_in_data
from .fes_technology_schema import harmonise_fes_headers

FES_RELEASE_YEARS = {
    "2021": (2020, 2025, 2030, 2035),
    "2022": (2020, 2025, 2030, 2035, 2040, 2045, 2050),
    "2024": (2020, 2025, 2030, 2035, 2040, 2045, 2050),
    "2025": (2025, 2030, 2035, 2040, 2045, 2050),
}

# Names are official FES pathway labels. Only earlier releases used abbreviations.
FES_SCENARIOS = {
    "2021": {"CT": "Consumer Transformation", "LW": "Leading the Way",
             "SP": "Steady Progression", "ST": "System Transformation"},
    "2022": {"CT": "Consumer Transformation", "LW": "Leading the Way",
             "FS": "Falling Short", "ST": "System Transformation"},
    "2024": {"EE": "Electric Engagement", "HT": "Holistic Transition",
             "HE": "Hydrogen Evolution", "CF": "Counterfactual"},
    "2025": {"EE": "Electric Engagement", "HT": "Holistic Transition",
             "HE": "Hydrogen Evolution", "FB": "Falling Behind"},
}

# Canonical GBHeat technology labels used in tech_half_hourly_profile.py.
# THESE ARE SCHEMA ALIASES, NOT CLAIMS OF PHYSICAL OR FUEL EQUIVALENCE.
# In particular 2024 'Biofuel' is kept as Biofuel, not silently converted
# to 'BioLPG'; users must decide explicitly whether to aggregate it.
CANONICAL_TECHNOLOGIES = (
    "ASHP", "GSHP", "Gas boiler", "Oil boiler", "Biomass boiler",
    "BioLPG boiler", "Hydrogen boiler", "Electric resistive", "Electric storage",
    "Community", "DH", "Hybrid (ASHP + Electric resistive)",
    "Hybrid (ASHP + BioLPG boiler)", "Hybrid (ASHP + Hydrogen boiler)",
)
FES_2025_SCHEMA_ALIASES = {
    "Fossil fuel communal heating": "Community",
    "Low carbon district heating": "DH",
}
FES_2024_SCHEMA_ALIASES = {}  # Biofuel deliberately remains distinct.


def _vintage(FES: str | int) -> str:
    value = str(FES).strip()
    if value not in FES_RELEASE_YEARS:
        raise ValueError(f"Unsupported FES vintage {FES!r}. Choose {list(FES_RELEASE_YEARS)}")
    return value


def available_FES_years(FES: str | int) -> tuple[int, ...]:
    """Available source-stock years (not interpolation years)."""
    return FES_RELEASE_YEARS[_vintage(FES)]


def available_FES_scenarios(FES: str | int) -> dict[str, str]:
    """Return code-to-full-pathway-name mapping for a specific FES vintage."""
    return FES_SCENARIOS[_vintage(FES)].copy()


def resolve_FES_scenario(FES: str | int, scenario: str) -> tuple[str, str]:
    """Return (short code, full name); refuse ambiguous cross-vintage aliases."""
    vintage = _vintage(FES)
    provided = str(scenario).strip().casefold()
    for code, full_name in FES_SCENARIOS[vintage].items():
        if provided in (code.casefold(), full_name.casefold()):
            return code, full_name
    raise ValueError(
        f"Unknown FES {vintage} pathway {scenario!r}. Available: "
        + ", ".join(f"{code} ({name})" for code, name in FES_SCENARIOS[vintage].items())
    )


def _source_path(vintage: str, year: int, data_dir: Path | None = None) -> Path:
    base = Path(data_dir) if data_dir is not None else path_in_data("FES_Spatial_Heat_Model", vintage)
    name = f"fes{vintage[-2:]}_la_level_outputs_{year}_residential_all_scenarios.csv"
    return base / name


def read_FES_heat_supply(
    FES: str | int,
    *,
    years: list[int] | tuple[int, ...] | None = None,
    data_dir: str | Path | None = None,
    harmonise_technologies: bool = True,
) -> pd.DataFrame:
    """Read the specified FES release, preserving its historical LA-name index.

    For newer releases the columns `Pathway` and `la_code` are exposed as
    `Scenario` (short code) and `CODE_x`. Original pathway names are retained
    in `Pathway` for provenance. Stock columns retain the `stock ` prefix.
    In 2024, Biofuel is NOT assumed equivalent to BioLPG.
    """
    vintage = _vintage(FES)
    chosen = available_FES_years(vintage) if years is None else tuple(int(y) for y in years)
    unknown = set(chosen) - set(available_FES_years(vintage))
    if unknown:
        raise ValueError(f"FES {vintage} has no stock files for years {sorted(unknown)}")
    frames = []
    for year in chosen:
        p = _source_path(vintage, year, Path(data_dir) if data_dir is not None else None)
        if not p.is_file():
            raise FileNotFoundError(f"Required FES {vintage} stock file missing: {p}")
        df = pd.read_csv(p, index_col=1)
        # Accept both historical and October 2026 NESO hybrid headers.
        df = harmonise_fes_headers(df, target="gbheat")
        df.index = df.index.astype(str).str.strip()
        if "Year" not in df or (pd.to_numeric(df["Year"], errors="coerce") != year).any():
            raise ValueError(f"Unexpected 'Year' values in {p}")
        if vintage in ("2024", "2025"):
            if "Pathway" not in df or "la_code" not in df:
                raise ValueError(f"Expected columns 'Pathway' and 'la_code' in {p}")
            df["Pathway"] = df["Pathway"].astype(str).str.strip()
            df.rename(columns={"la_code": "CODE_x"}, inplace=True)
            df.insert(2, "Scenario", df["Pathway"].map(
                lambda label: resolve_FES_scenario(vintage, label)[0]))
            # Names differ between releases; retain original Pathway column and
            # the 2024 Biofuel names for transparency.
            if harmonise_technologies:
                aliases = FES_2025_SCHEMA_ALIASES if vintage == "2025" else FES_2024_SCHEMA_ALIASES
                df.rename(columns={f"stock {src}": f"stock {dst}" for src, dst in aliases.items()}, inplace=True)
        else:
            if "Scenario" not in df or "CODE_x" not in df:
                raise ValueError(f"Expected legacy columns 'Scenario' and 'CODE_x' in {p}")
        # Explicit validation, avoiding silent zeroed stocks downstream.
        if df["Scenario"].isna().any():
            raise ValueError(f"Unrecognised scenario in {p}")
        tech_columns = [c for c in df if c.startswith("stock ") and c not in ("stock Total", "stock TotalHPs")]
        if vintage in ("2021", "2022"):
            # Historic sources legitimately omit technologies when their entire
            # year has zero stock. Make them explicit zeros, matching legacy
            # concat(...).fillna(0) semantics across the complete release.
            for tech in CANONICAL_TECHNOLOGIES:
                col = f"stock {tech}"
                if col not in df:
                    df[col] = 0.0
            tech_columns = [c for c in df if c.startswith("stock ") and c not in ("stock Total", "stock TotalHPs")]
        if len(tech_columns) != 14:
            raise ValueError(f"Expected 14 technology stock columns in {p}; found {len(tech_columns)}: {tech_columns}")
        stocks = df[tech_columns].apply(pd.to_numeric, errors="coerce")
        if vintage in ("2021", "2022"):
            # Legacy FES tables mark some not-deployed technology/scenario
            # combinations NA; previous read concatenation converted to zero.
            stocks = stocks.fillna(0.0)
            df[tech_columns] = stocks
        if stocks.isna().any().any() or (stocks < 0).any().any():
            raise ValueError(f"Null, nonnumeric or negative heating technology stocks in {p}")
        if df[["CODE_x", "Scenario"]].duplicated().any():
            raise ValueError(f"Duplicate LA code and scenario in {p}")
        frames.append(df)
    return pd.concat(frames, axis=0).fillna(0) if frames else pd.DataFrame()


def year_FES_heat_supply(year, FES, scenario=None, *, data_dir=None, harmonise_technologies=True):
    """Select a release's latest published stock year <= requested target year.

    For 2024/25 outputs `Scenario` contains short unambiguous pathway codes
    EE/HT/HE/CF or EE/HT/HE/FB; `Pathway` retains published full names.
    """
    vintage = _vintage(FES)
    if scenario is None:
        raise ValueError("A FES pathway is required; use available_FES_scenarios(FES)")
    code, _ = resolve_FES_scenario(vintage, scenario)
    target_year = int(year)
    candidates = [y for y in FES_RELEASE_YEARS[vintage] if y <= target_year]
    if not candidates:
        raise ValueError(f"FES {vintage} has no stock projections at or before {target_year}; earliest is {FES_RELEASE_YEARS[vintage][0]}")
    selected_year = max(candidates)
    df = read_FES_heat_supply(vintage, years=[selected_year], data_dir=data_dir,
                              harmonise_technologies=harmonise_technologies)
    result = df.loc[df["Scenario"].eq(code)].copy()
    if result.empty:
        raise ValueError(f"FES {vintage}, year {selected_year}: no rows for scenario {code}")
    return result
