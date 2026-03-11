# src/gbheatmodel/FES_heat_supply_data.py

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .path import path_in_data


def read_FES_heat_supply(FES: str) -> pd.DataFrame:
    """
    Read all available FES spatial heat supply data for a given FES vintage.

    Parameters
    ----------
    FES : {"2021", "2022"}
        FES dataset version.

    Returns
    -------
    DataFrame
        Concatenated FES data across all years for the chosen vintage.
        Index is column 1 of the CSV (typically LA name / code).
    """
    FES = str(FES)

    if FES == "2021":
        years = ["2020", "2025", "2030", "2035"]
        pattern = "la_level_outputs_{year}_domestic_all_scenarios_org_updated.csv"
    elif FES == "2022":
        years = ["2020", "2025", "2030", "2035", "2040", "2045", "2050"]
        pattern = "fes22_la_level_outputs_{year}_residential_all_scenarios.csv"
    else:
        raise ValueError(f"Unsupported FES vintage: {FES!r}. Expected '2021' or '2022'.")

    dfs: list[pd.DataFrame] = []

    # Use path_in_data, same style as heat_pattern.py
    # e.g. data/FES_Spatial_Heat_Model/2022
    base_dir: Path = path_in_data("FES_Spatial_Heat_Model", FES)

    for year in years:
        file_path = base_dir / pattern.format(year=year)
        df_FES = pd.read_csv(file_path, index_col=1)
        dfs.append(df_FES)

    df = pd.concat(dfs, axis=0).fillna(0)
    return df


def year_FES_heat_supply(year, FES, scenario=None):

    if FES == '2021':
        year_list = np.array([2020, 2025, 2030, 2035])
        closest_year = year_list[year_list <= year].max()
    
    elif FES == '2022':
        year_list = np.array([2020, 2025, 2030, 2035, 2040, 2045, 2050])
        closest_year = year_list[year_list <= year].max()

    df = read_FES_heat_supply(FES)
    df = df.loc[df['Year'] == closest_year]
    df = df.loc[df['Scenario'] == scenario]

    return df


if __name__ == "__main__":
    # Simple manual test
    df_test = year_FES_heat_supply(2031, "2021", scenario="LW")
    print(df_test.head())
    print(f"Rows: {len(df_test)}")
