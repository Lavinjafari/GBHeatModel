# src/gbheatmodel/runner.py
from __future__ import annotations

from typing import Dict, Any

import geopandas as gpd
import pandas as pd  # noqa: F401

from .path import path_in_data
from .LA_overlaps_within_grid_squares import calc_LA_overlap_within_grid_square
from . import heat_tech_distribution
from .tech_half_hourly_profile import scaling_half_hourly_profiles_grid_sqs
from .Grid_squares_heat_tech_demand import calculate_heat_demand_for_grid_squares


def run_heat_demand_pipeline(
    weather_year: int,
    future_year: int,
    FES_year: str,
    scenario: str,
) -> Dict[str, Any]:
    """
    High-level heating demand pipeline for a single (weather_year, future_year, scenario).

    Returns
    -------
    dict
        {
          "LA_overlaps": GeoDataFrame,
          "merged_FES": DataFrame,
          "total_dwellings": DataFrame,
          "grid_square_hd": DataFrame,
          "profiles": dict[grid_id -> DataFrame]
        }
    """

    # 1. Geometry: LAs & grid squares
    la_path = path_in_data(
        "LAs_shapefile_2021",
        "LAD_DEC_2021_GB_BFC.shp",
    )
    grids_path = path_in_data("UK_Atlite_Grid_sq.gpkg")

    la_shapefile = gpd.read_file(la_path)
    grid_squares = gpd.read_file(grids_path)

    # 2. LA–grid overlaps
    LA_overlaps = calc_LA_overlap_within_grid_square(
        grid_squares=grid_squares,
        LA_shapefile=la_shapefile,
        weather_year=weather_year,
    )

    # 3. Merge FES + shapefile + overlaps at LA level
    # IMPORTANT: positional arguments only – no FES_year keyword!
    merged_FES = heat_tech_distribution.merge_shapefile_FES_heating_tech_file(
        grid_squares,
        LA_overlaps,
        future_year,
        FES_year,
        scenario,
        weather_year,
    )

    # 4. Distribute heating technologies to grid squares
    total_dwellings = heat_tech_distribution.distribute_all_heating_techs_to_grids(
        merged_FES
    )

    # 5. Aggregate demand per grid square & tech using total_dwellings directly
    grid_square_hd = calculate_heat_demand_for_grid_squares(
        total_dwellings=total_dwellings,
    )

    # 6. Generate half-hourly profiles per grid square using precomputed patterns
    pattern_profile_path = path_in_data(
        "heat_demand_profiles_patterns",
        f"HD_heat_patterns_{weather_year}",
    )

    profiles = scaling_half_hourly_profiles_grid_sqs(
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
        "total_dwellings": total_dwellings,
        "grid_square_hd": grid_square_hd,
        "profiles": profiles,
    }
