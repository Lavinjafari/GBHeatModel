
import os
from typing import Dict, Optional

import geopandas as gpd
import pandas as pd

from . import FES_scaling_factor
from . import heat_tech_distribution
from . import LA_overlaps_within_grid_squares
from .path import path_in_data, ensure_dir


def base_heat_pattern_per_technology() -> pd.DataFrame:
    """
    Returns heat demand distribution (daytime, bi-modal, continuous) for 1 unit
    of each heating technology, normalized to fractions.
    """
    tech_patterns = {
        # 'ASHP': {'daytime': 28, 'bi-modal': 8, 'continuous': 64},
        "ASHP": {"daytime": 30, "bi-modal": 9, "continuous": 61},
        # 'GSHP': {'daytime': 28, 'bi-modal': 8, 'continuous': 64},
        "GSHP": {"daytime": 21, "bi-modal": 5, "continuous": 74},
        "Gas boiler": {"daytime": 46, "bi-modal": 34, "continuous": 20},
        "Electric storage": {"daytime": 0, "bi-modal": 0, "continuous": 100},
        "Hybrid (ASHP + Electric resistive)": {
            "daytime": 46,
            "bi-modal": 34,
            "continuous": 20,
        },
    }

    # Apply default pattern for remaining technologies
    other_techs = [
        "Oil boiler",
        "Biomass boiler",
        "Biofuel boiler",                 # FES 2024
        "BioLPG boiler",                  # FES 2025
        "Community",
        "Hybrid (ASHP + Biofuel boiler)",  # FES 2024
        "Hybrid (ASHP + BioLPG boiler)",   # FES 2025
        "Hybrid (ASHP + Hydrogen boiler)",
        "DH",
        "Electric resistive",
        "Hydrogen boiler",
    ]

    default_pattern = {"daytime": 46, "bi-modal": 34, "continuous": 20}
    for tech in other_techs:
        tech_patterns[tech] = default_pattern.copy()

    # Normalize to fractions
    base_pattern = pd.DataFrame(tech_patterns).T / 100.0
    base_pattern.index.name = "Technology"
    return base_pattern



def scaling_half_hourly_profiles_grid_sqs(
    pattern_profile_path,
    total_dwellings,
    weather_year,
    future_year,
    FES_year,
    FES_scenario,
    output_dir=None
):
    """
    FAST VERSION — identical to old behaviour, only paths updated.
    Scales half-hourly heating profiles by grid square based on:
    - Technology distribution (dwellings per grid per tech)
    - FES scenario scaling factor
    """

    # --- 1. Clean and reindex  ---
    # # total_dwellings = total_dwellings.copy()
    # total_dwellings["Grid_ID"] = total_dwellings["Grid_ID"].astype(str).str.strip()
    # total_dwellings.set_index("Grid_ID", inplace=True)

    # # --- 2. Load grid IDs from air temperature file 
    # air_temp_path = path_in_data("air_temp", f"air_temp_{weather_year}.csv")
    # air_temp_df = pd.read_csv(air_temp_path, index_col=0)
    # grid_sqs = [str(gid).strip() for gid in air_temp_df.columns]
    # 1. Ensure consistent string index for Grid_ID
    total_dwellings = total_dwellings.copy()
    total_dwellings["Grid_ID"] = total_dwellings["Grid_ID"].astype(str).str.strip()
    total_dwellings.set_index("Grid_ID", inplace=True)

    # 2. Use unique grid IDs from total_dwellings (always 739)
    grid_sqs = total_dwellings.index.unique().tolist()
    # Optional debug:
    # print(f"[DEBUG] Using {len(grid_sqs)} grid squares from total_dwellings")


    # --- 3. Get FES scaling + base pattern ---
    FES_scaling = float(
        FES_scaling_factor.FES_scaling_factor_calc(
            future_year,
            FES_year,
            FES_scenario,
        )
    )
    base_pattern = base_heat_pattern_per_technology()
    
    # Identify technologies actually present in the selected FES release.
    technology_columns = [
        col for col in total_dwellings.columns
        if col in base_pattern.index
    ]

    if len(technology_columns) != 14:
        raise ValueError(
            f"Expected 14 FES heating technologies, "
            f"found {len(technology_columns)}: {technology_columns}"
        )

    # Prevent unexpected numeric technology columns from being ignored.
    metadata_columns = {
        "Grid_ID", "LA_Code", "Local_Authority",
        "Year", "Scenario", "Pathway", "Sector", "CODE_x"
    }

    unexpected_columns = [
        col for col in total_dwellings.columns
        if col not in technology_columns
        and col not in metadata_columns
    ]

    if unexpected_columns:
        raise ValueError(
            f"Unrecognised columns in grid-level stock data: "
            f"{unexpected_columns}"
        )

    # --- 4. Output directory (updated to use path_in_data) ---
    if output_dir is None:
        output_dir = path_in_data(
            "outputs",
            "heating_profiles",
            f"{weather_year}_{FES_year}_{FES_scenario}_{future_year}"
        )
    else:
        output_dir = os.fspath(output_dir)

    # Make sure output folders exist
    ensure_dir(path_in_data("outputs"))
    os.makedirs(output_dir, exist_ok=True)

    # --- 5. Try early load of all existing profiles ---
    existing_profiles_dict = {}
    all_exist = True

    for grid_id in grid_sqs:
        file_name = (
            f"half_hourly_heat_profile_{grid_id}_{weather_year}_"
            f"{FES_year}_{FES_scenario}_{future_year}.csv"
        )
        file_path = os.path.join(output_dir, file_name)

        if os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col=0)
            df.index = pd.to_datetime(df.index)
            existing_profiles_dict[grid_id] = df
        else:
            all_exist = False
            break 

    if all_exist:
        print("✅ All heating profiles already exist. Loading from disk.")
        return existing_profiles_dict

    # --- 6. Main scaling loo ---
    scaled_profiles_dict = {}

    for grid_id in grid_sqs:

        if grid_id not in total_dwellings.index:
            print(f"⚠️ Skipping {grid_id} — no dwelling data.")
            continue

        pattern_file = os.path.join(pattern_profile_path, f"({grid_id})_{weather_year}.csv")
        if not os.path.exists(pattern_file):
            print(f"⚠️ Skipping {grid_id} — pattern file missing.")
            continue

        try:
            pattern_profile = pd.read_csv(pattern_file, index_col=0)
        except Exception as e:
            print(f"⚠️ Error loading pattern for {grid_id}: {e}")
            continue

        tech_dwellings = total_dwellings.loc[grid_id]
        if isinstance(tech_dwellings, pd.DataFrame):
            tech_dwellings = tech_dwellings.iloc[0]

        data = {
            tech: (
                pattern_profile["daytime"].values * float(base_pattern.loc[tech, "daytime"])
                + pattern_profile["bi-modal"].values * float(base_pattern.loc[tech, "bi-modal"])
                + pattern_profile["continuous"].values * float(base_pattern.loc[tech, "continuous"])
            ) * float(tech_dwellings[tech]) * FES_scaling
            for tech in technology_columns
        }

        scaled_profile = pd.DataFrame.from_dict(data, orient="columns")
        scaled_profile.index = pd.date_range(
            start=f"{future_year}-01-01", periods=17520, freq="30min"
        )

        output_path = os.path.join(
            output_dir,
            f"half_hourly_heat_profile_{grid_id}_{weather_year}_"
            f"{FES_year}_{FES_scenario}_{future_year}.csv"
        )
        scaled_profile.to_csv(output_path)
        print(f"✅ Saved: {output_path}")

        scaled_profiles_dict[grid_id] = scaled_profile

    return scaled_profiles_dict

if __name__ == "__main__":
    weather_year = 2010
    future_year = 2050
    FES_year = "2022"
    FES_scenario = "LW"  # Low Warm scenario

    # Load shapefile and grid squares using centralised paths
    LA_path = path_in_data(
        "LAs_shapefile_2021",
        "LAD_DEC_2021_GB_BFC.shp",
    )
    grids_path = path_in_data(
        "UK_Atlite_Grid_sq.gpkg"
    )
    LA_shapefile = gpd.read_file(LA_path)
    grid_squares = gpd.read_file(grids_path)

    air_temp_path = path_in_data(
         "air_temp", f"air_temp_{weather_year}.csv"
    )
    air_temp_df = pd.read_csv(air_temp_path, index_col=0)
    grid_sqs = air_temp_df.columns  # List of grid square IDs

    LA_overlaps = LA_overlaps_within_gird_squares.calc_LA_overlap_within_grid_square(
        grid_squares,
        LA_shapefile,
        weather_year,
    )

    df_merged = heat_tech_distribution.merge_shapefile_FES_heating_tech_file(
        grid_squares,
        LA_overlaps,
        future_year,
        FES_year,
        FES_scenario,
        weather_year,
    )

    total_dwellings = heat_tech_distribution.distribute_all_heating_techs_to_grids(
        df_merged,
        LA_overlaps,
        future_year,
        FES_year,
        FES_scenario,
        weather_year,
    )

    pattern_profile_path = path_in_data(
        "heat_demand_profiles_patterns",
        f"HD_heat_patterns_{weather_year}",
    )

    scaled_heat_profiles = scaling_half_hourly_profiles_grid_sqs(
        pattern_profile_path,
        total_dwellings,
        weather_year,
        future_year,
        FES_year,
        FES_scenario,
        output_dir=None,
    )
