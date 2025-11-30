# src/gbheatmodel/heat_pattern.py

from __future__ import annotations

import pandas as pd
import geopandas as gpd

# internal package imports
from . import Grid_squares_heat_tech_demand
from . import LA_overlaps_within_grid_squares
from .path import path_in_data


def heat_demand_for_one_pattern_for_one_day(
    total_dwellings_pattern: float,
    heating_pattern: str,
    Td: float,
) -> float:
    """
    Calculate the heat demand for one day for a given number of dwellings,
    heating pattern, and average day temperature.

    Parameters
    ----------
    total_dwellings_pattern : float
        Number of dwellings following this pattern.
    heating_pattern : {"daytime", "bi-modal", "continuous", "ASHP", "GSHP"}
        Type of heating pattern or technology.
    Td : float
        Average daily external temperature [°C].

    Returns
    -------
    float
        Total daily heat demand for all dwellings using this pattern [kWh/day].
    """
    if heating_pattern == "daytime":
        C = {"TBp": 14.3, "mp1": -5.39, "cp1": 88.8, "mp2": -0.94, "cp2": 25.0, "R2": 0.97}
    elif heating_pattern == "bi-modal":
        C = {"TBp": 13.9, "mp1": -5.22, "cp1": 83.7, "mp2": -0.82, "cp2": 22.4, "R2": 0.97}
    elif heating_pattern == "continuous":
        C = {"TBp": 14.3, "mp1": -6.18, "cp1": 102.6, "mp2": -1.24, "cp2": 31.8, "R2": 0.98}
    elif heating_pattern == "ASHP":
        C = {"TBp": 14.3, "mp1": -5.85, "cp1": 96.7, "mp2": -1.1, "cp2": 28.7}
    elif heating_pattern == "GSHP":
        C = {"TBp": 14.3, "mp1": -5.96, "cp1": 98.7, "mp2": -1.15, "cp2": 29.8}
    else:
        raise ValueError(f"Unknown heating_pattern: {heating_pattern!r}")

    if Td < C["TBp"]:
        HD = C["mp1"] * Td + C["cp1"]
    else:
        HD = C["mp2"] * Td + C["cp2"]

    return float(HD * total_dwellings_pattern)


def grid_sq_heat_pattern_totals(
    grid_squares: gpd.GeoDataFrame,
    LA_shapefile: gpd.GeoDataFrame,
    weather_year: int,
    future_year: int,
    FES: str,
    scenario: str,
) -> dict[str, pd.DataFrame]:
    """
    Calculate the heat demand patterns for grid squares based on technology mixes.

    Returns
    -------
    dict[str, DataFrame]
        Mapping: grid_id -> DataFrame with rows = technologies,
        columns = ['daytime', 'bi-modal', 'continuous'] scaled by dwellings.
    """
    # ---- 1. Grid IDs from temperature file ---------------------------------

    air_temp_path = path_in_data(
        "air_temp", f"air_temp_{weather_year}.csv"
    )
    try:
        grid_sq = pd.read_csv(air_temp_path, index_col=0).columns
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Could not find air temperature data file at: {air_temp_path}"
        ) from e

    # ---- 2. LA overlaps and heat demand per grid square ---------------------

    LA_overlaps = LA_overlaps_within_grid_squares.calc_LA_overlap_within_grid_square(
        grid_squares, LA_shapefile, weather_year
    )

    df = Grid_squares_heat_tech_demand.calculate_heat_demand_for_grid_squares(
        LA_overlaps,
        weather_year,
        future_year,
        FES,
        scenario,
        LA_shapefile,
        grid_squares,
    )

    # ---- 3. Clean up index / columns ----------------------------------------

    df.columns = df.columns.str.replace(r"stock ", "", regex=True)

    index_replacements = {
        "Chiltern District": "Chiltern",
        "South Bucks District": "South Bucks",
        "Wycombe District": "Wycombe",
        "Aylesbury Vale District": "Aylesbury Vale",
    }

    df.index = pd.Series(df.index).replace(index_replacements).values
    df.set_index("Grid_ID", inplace=True)
    df.index = df.index.astype(str)

    missing_squares = set(grid_sq) - set(df.index)
    if missing_squares:
        raise ValueError(
            f"Grid squares {missing_squares} not found in heat demand data"
        )

    list_of_tech = df.columns.values[3:18]
    df[list_of_tech] = df[list_of_tech].apply(pd.to_numeric, errors="coerce")

    # ---- 4. Heating-pattern mapping -----------------------------------------

    heating_pattern_to_tech = {
        "ASHP": {"daytime": 30, "bi-modal": 9, "continuous": 61},
        "GSHP": {"daytime": 21, "bi-modal": 5, "continuous": 74},
        "Gas boiler": {"daytime": 46, "bi-modal": 34, "continuous": 20},
    }

    dict_grid_sq: dict[str, pd.DataFrame] = {}

    for grid_id in grid_sq:
        df_heat_pattern = pd.DataFrame(heating_pattern_to_tech)

        list_of_tech_ = [
            tech
            for tech in list_of_tech
            if tech not in ["ASHP", "GSHP", "Gas boiler", "Electric storage"]
        ]

        for tech in list_of_tech_:
            df_heat_pattern[tech] = {"daytime": 46, "bi-modal": 34, "continuous": 20}

        df_heat_pattern["Electric storage"] = {
            "daytime": 0,
            "bi-modal": 0,
            "continuous": 100,
        }
        df_heat_pattern["Hybrid (ASHP + Electric resistive)"] = {
            "daytime": 46,
            "bi-modal": 34,
            "continuous": 20,
        }

        df_heat_pattern = df_heat_pattern.T / 100

        for tech in list_of_tech:
            tech_value = pd.to_numeric(df.loc[grid_id, tech], errors="coerce")

            if pd.isna(tech_value):
                print(f"Warning: NA value for {tech!r} in grid square {grid_id}")
                tech_value = 0.0

            df_heat_pattern.loc[tech] = tech_value * df_heat_pattern.loc[tech]

        dict_grid_sq[grid_id] = df_heat_pattern

    return dict_grid_sq


if __name__ == "__main__":
    # simple manual test for one grid
    weather_year = 2012
    FES = "2022"
    future_year = 2050
    scenario = "LW"
    grid_id = "-0.25_50.75"

    LA_path = path_in_data(
        "LAs_shapefile_2021",
        "LAD_DEC_2021_GB_BFC.shp",
    )
    grids_path = path_in_data(
        "UK_Atlite_Grid_sq.gpkg"
    )

    LA_shapefile = gpd.read_file(LA_path)
    grid_squares = gpd.read_file(grids_path)

    grid_sq_heat_pattern_total = grid_sq_heat_pattern_totals(
        grid_squares,
        LA_shapefile,
        weather_year,
        future_year,
        FES,
        scenario,
    )

    grid_totals = grid_sq_heat_pattern_total[grid_id].sum(axis=1)
    print(grid_totals)
