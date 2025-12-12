# src/gbheatmodel/runner.py
from __future__ import annotations
import os
from typing import Dict, Any

import geopandas as gpd
import pandas as pd  # noqa: F401

from .path import path_in_data, ensure_dir
from .LA_overlaps_within_grid_squares import calc_LA_overlap_within_grid_square
from . import heat_tech_distribution
from .tech_half_hourly_profile import scaling_half_hourly_profiles_grid_sqs
from . import Grid_squares_heat_tech_demand
from . import cop
from .electric_demand import electric_demand_for_heat
import time


def profiles_output_dir(
    weather_year,
    future_year,
    FES_year, 
    scenario,
    ):
    """
    Build the expected output directory for heating profiles for a given run.
    This does NOT create the directory; it only returns the path.
    """
    return path_in_data(
        "outputs",
        "heating_profiles",
        f"{weather_year}_{FES_year}_{scenario}_{future_year}",
    )



def run_heat_demand_pipeline(
    weather_year,
    future_year,
    FES_year,
    scenario,
    skip_if_profiles_exist,
):

    """
    High-level heating demand pipeline for a single (weather_year, future_year, scenario).

    Returns
    -------
    dict
        {
          "LA_overlaps": GeoDataFrame,
          "df_merged": DataFrame,
          "total_dwellings": DataFrame,
          "grid_square_hd": DataFrame,
          "profiles": dict[grid_id -> DataFrame]
        }
    """
    # 1. Geometry: LAs & grid squares
    LA_path = path_in_data(
        "LAs_shapefile_2021",
        "LAD_DEC_2021_GB_BFC.shp",
    )
    grids_path = path_in_data("UK_Atlite_Grid_sq.gpkg")

    LA_shapefile = gpd.read_file(LA_path)
    grid_squares = gpd.read_file(grids_path)
    

    # 2. LA–grid overlaps
    LA_overlaps = calc_LA_overlap_within_grid_square(
        grid_squares=grid_squares,
        LA_shapefile=LA_shapefile,
        weather_year=weather_year,
    )


    # 3. Merge FES + shapefile + overlaps at LA level
    # IMPORTANT: positional arguments only – no FES_year keyword!
    df_merged = heat_tech_distribution.merge_shapefile_FES_heating_tech_file(
        grid_squares,
        LA_overlaps,
        future_year,
        FES_year,
        scenario,
        weather_year,
    )
    # 4. Distribute heating technologies to grid squares
    distributed_df = heat_tech_distribution.distribute_all_heating_techs_to_grids(df_merged)

    # 5. Aggregate heating technologies to grid squares
    total_dwellings = Grid_squares_heat_tech_demand.calculate_heat_demand_for_grid_squares(distributed_df)


    # 7. Generate half-hourly profiles per grid square using precomputed patterns
    pattern_profile_path = path_in_data(
        "heat_demand_profiles_patterns",
        f"HD_heat_patterns_{weather_year}",
    )

    HD_profiles = scaling_half_hourly_profiles_grid_sqs(
        pattern_profile_path=pattern_profile_path,
        total_dwellings=total_dwellings,
        weather_year=weather_year,
        future_year=future_year,
        FES_year=FES_year,
        FES_scenario=scenario,
        output_dir=None,
    )
    
    return {
        "LA_overlaps": LA_overlaps,
        "df_merged": df_merged,
        "distributed_df": distributed_df,
        "total_dwellings": total_dwellings,
        "HD_profiles": HD_profiles,
    }
    
def run_heat_profiles_only(
    weather_year,
    future_year,
    FES_year,
    scenario,
):
    """
    Convenience wrapper that runs the full heat demand pipeline
    and returns only the half-hourly profiles per grid square.

    Returns
    -------
    dict
        Mapping grid_id -> DataFrame (index: timestamp, columns: technologies).
    """
    HD_profiles = run_heat_demand_pipeline(
        weather_year=weather_year,
        future_year=future_year,
        FES_year=FES_year,
        scenario=scenario,
        skip_if_profiles_exist=False,
    )
    return HD_profiles["HD_profiles"]


def run_cop_profiles(
    weather_year,
    future_year,
    performance_level,
    save=True,
):
    """
    Compute half-hourly COP profiles for ASHP and GSHP for all grid squares.

    Loads:
      data/air_temp/average_day_air_temp_<weather_year>.csv

    Saves (optional):
      data/outputs/COP_Profiles/ASHP_<performance_level>_<weather_year>_<future_year>.csv
      data/outputs/COP_Profiles/GSHP_<performance_level>_<weather_year>_<future_year>.csv

    Returns
    -------
    dict
      {"ASHP": df_cop_ASHP, "GSHP": df_cop_GSHP}
    """

    # Load daily average temperatures
    avg_air_temp_path = path_in_data("air_temp", f"average_day_air_temp_{weather_year}.csv")
    air_temp_daily = pd.read_csv(avg_air_temp_path, index_col=0)

    # Standardize to daily datetime index
    air_temp_daily.index = pd.date_range(
        start=f"{weather_year}-01-01",
        periods=len(air_temp_daily),
        freq="D",
    )

    # Compute COP profiles using core functions (no I/O inside core)
    df_cop_ASHP = cop.day_cop_for_year_grid_sq(
        heat_pump_type="ASHP",
        performance_level=performance_level,
        future_year=future_year,
        weather_year=weather_year,
        air_temp_daily=air_temp_daily,
    )

    df_cop_GSHP = cop.day_cop_for_year_grid_sq(
        heat_pump_type="GSHP",
        performance_level=performance_level,
        future_year=future_year,
        weather_year=weather_year,
        air_temp_daily=air_temp_daily,
    )

    if save:
        out_dir = path_in_data("outputs", "COP_Profiles")
        ensure_dir(out_dir)

        ASHP_path = os.path.join(out_dir, f"ASHP_{performance_level}_{weather_year}_{future_year}.csv")
        GSHP_path = os.path.join(out_dir, f"GSHP_{performance_level}_{weather_year}_{future_year}.csv")

        df_cop_ASHP.to_csv(ASHP_path)
        df_cop_GSHP.to_csv(GSHP_path)

    return {"ASHP": df_cop_ASHP, "GSHP": df_cop_GSHP}

def run_electric_demand(
    HD_profiles,
    df_cop_ASHP,
    df_cop_GSHP,
    FES_year,
    scenario,
    future_year,
    save=True,
):
    """
    Convert heat demand profiles into electric demand profiles using COP.

    Parameters
    ----------
    HD_profiles
        Dict: grid_id -> heat demand DF (half-hourly), i.e. scaled_profiles_dict.
    df_cop_ashp, df_cop_gshp
        COP DataFrames with index=time and columns=grid_ids.
    FES_year, scenario, future_year
        Used only for output folder naming if save=True.
    save
        If True, saves per-grid CSVs under outputs/electric_demand/<...>/.

    Returns
    -------
    dict
        Dict: grid_id -> electric demand DF (half-hourly)
    """

    grid_sqs = list(HD_profiles.keys())

    ed_grid_sqs =  electric_demand_for_heat(
        HD_profiles=HD_profiles,
        grid_sqs=grid_sqs,
        df_ASHP=df_cop_ASHP,
        df_GSHP=df_cop_GSHP,
    )

    if save:
        out_dir = path_in_data("outputs", "electric_demand", f"{FES_year}_{scenario}_{future_year}")
        ensure_dir(out_dir)

        for grid_id, df in ed_grid_sqs.items():
            file_name = f"elec_demand_{grid_id}_{FES_year}_{scenario}_{future_year}.csv"
            file_path = os.path.join(out_dir, file_name)
            df.to_csv(file_path)

    return ed_grid_sqs