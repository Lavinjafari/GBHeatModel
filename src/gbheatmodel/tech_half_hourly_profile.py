import pandas as pd
import numpy as np
import FES_shapefile_LAs_matching
import os
import FES_scaling_factor
import heat_tech_distribution
import LA_overlaps_within_gird_squares
import geopandas as gpd
from typing import Dict, Optional
from typing import Dict

 


def base_heat_pattern_per_technology():
    """
    Returns heat demand distribution (daytime, bi-modal, continuous) for 1 unit 
    of each heating technology, normalized to fractions.
    """
    tech_patterns = {
        #'ASHP': {'daytime': 28, 'bi-modal': 8, 'continuous': 64},
        'ASHP': {'daytime': 30, 'bi-modal': 9, 'continuous': 61},
        #'GSHP': {'daytime': 28, 'bi-modal': 8, 'continuous': 64},
        'GSHP': {'daytime': 21, 'bi-modal': 5, 'continuous': 74},
        'Gas boiler': {'daytime': 46, 'bi-modal': 34, 'continuous': 20},
        'Electric storage': {'daytime': 0, 'bi-modal': 0, 'continuous': 100},
        'Hybrid (ASHP + Electric resistive)': {'daytime': 46, 'bi-modal': 34, 'continuous': 20},
    }

    # Apply default pattern for remaining technologies
    other_techs = [
        'Oil boiler', 'Biomass boiler', 'BioLPG boiler',
        'Community', 'Hybrid (ASHP + BioLPG boiler)', 'Hybrid (ASHP + Hydrogen boiler)',
        'DH', 'Electric resistive', 'Hydrogen boiler'
    ]
    
    default_pattern = {'daytime': 46, 'bi-modal': 34, 'continuous': 20}
    for tech in other_techs:
        tech_patterns[tech] = default_pattern.copy()

    # Normalize to fractions
    base_pattern = pd.DataFrame(tech_patterns).T / 100
    base_pattern.index.name = "Technology"
    return base_pattern


def scaling_half_hourly_profiles_grid_sqs(
    pattern_profile_path,
    total_dwellings,
    weather_year,
    future_year,
    FES_year,
    FES_scenario,
    output_dir=None):
    """
    Scales half-hourly heating profiles by grid square based on:
    - Technology distribution (dwellings per grid per tech)
    - FES scenario scaling factor

    Parameters:
    -----------
    pattern_profile_path : str
        Directory path to heat demand profile CSVs.
    total_dwellings : pd.DataFrame
        DataFrame with rows indexed by Grid_ID and columns as technology types.
    weather_year : int
        Year for temperature and pattern profiles (e.g. 2012).
    future_year : int
        Year for projecting future profiles (e.g. 2030).
    FES_year : str
        FES dataset version (e.g. '2022').
    FES_scenario : str
        Scenario name (e.g. 'CT', 'LW').
    output_dir : str, optional
        Directory to save outputs. Auto-generated if not given.

    Returns:
    --------
    Dict[str, pd.DataFrame]
        Dictionary mapping grid_id to scaled profile (17520xN_technologies).
    """
 

    # Clean and reindex
    total_dwellings['Grid_ID'] = total_dwellings['Grid_ID'].astype(str).str.strip()
    total_dwellings.set_index('Grid_ID', inplace=True)

    # Load grid IDs from air temp data
    air_temp_path = f'data/LA_UK/new_version/air_temp_new/air_temp_{weather_year}.csv'
    air_temp_df = pd.read_csv(air_temp_path, index_col=0)
    grid_sqs = [str(gid).strip() for gid in air_temp_df.columns]

    # Get scaling factor and base pattern
    FES_scaling = float(FES_scaling_factor.FES_scaling_factor_calc(future_year, FES_year, FES_scenario))
    base_pattern = base_heat_pattern_per_technology()

    if output_dir is None:
        output_dir = f"data/LA_UK/new_version/outputs/heating_profiles/{weather_year}_{FES_year}_{FES_scenario}_{future_year}"
    os.makedirs(output_dir, exist_ok=True)
    
    existing_profiles_dict = {}
    all_exist = True

    for grid_id in grid_sqs:
        file_name = f"half_hourly_heat_profile_{grid_id}_{weather_year}_{FES_year}_{FES_scenario}_{future_year}.csv"
        file_path = os.path.join(output_dir, file_name)
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col=0)
            df.index = pd.to_datetime(df.index)
            existing_profiles_dict[grid_id] = df
        else:
            all_exist = False
            break  # One missing file is enough to skip loading

    # If all profiles exist, return them early
    if all_exist:
        print("✅ All heating profiles already exist. Loading from disk.")
        return existing_profiles_dict

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

        # scaled_profile = pd.DataFrame({
        #     tech: (
        #         pattern_profile['daytime'].values * float(base_pattern.loc[tech, 'daytime']) +
        #         pattern_profile['bi-modal'].values * float(base_pattern.loc[tech, 'bi-modal']) +
        #         pattern_profile['continuous'].values * float(base_pattern.loc[tech, 'continuous'])
        #     ) * float(tech_dwellings.get(tech, 0)) * FES_scaling
        #     for tech in base_pattern.index
        # })
        data = {
            tech: (
                pattern_profile['daytime'].values * float(base_pattern.loc[tech, 'daytime']) +
                pattern_profile['bi-modal'].values * float(base_pattern.loc[tech, 'bi-modal']) +
                pattern_profile['continuous'].values * float(base_pattern.loc[tech, 'continuous'])
            ) * float(tech_dwellings.get(tech, 0)) * FES_scaling
            for tech in base_pattern.index
        }

        scaled_profile = pd.DataFrame.from_dict(data, orient='columns')


        scaled_profile.index = pd.date_range(start=f'{future_year}-01-01', periods=17520, freq='30min')

        output_path = os.path.join(output_dir, f"half_hourly_heat_profile_{grid_id}_{weather_year}_{FES_year}_{FES_scenario}_{future_year}.csv")
        scaled_profile.to_csv(output_path)
        print(f"✅ Saved: {output_path}")

        scaled_profiles_dict[grid_id] = scaled_profile

    return scaled_profiles_dict


if __name__ == "__main__":
    weather_year = 2010
    future_year = 2050
    FES_year = '2022'
    FES_scenario = 'LW'  # Low Warm scenario
    
    LA_shapefile = gpd.read_file(r'data\LA_UK\new_version\UK_LAs_Boundaries_files\LAs_shapefile_2021\LAD_DEC_2021_GB_BFC.shp')
    grid_squares = gpd.read_file(r'data\LA_UK\new_version\data_call\UK_Atlite_Grid_sq.gpkg')
    air_temp_df = pd.read_csv('data/LA_UK/new_version/air_temp_new/air_temp_2012.csv', index_col=0)
    grid_sqs = air_temp_df.columns  # List of grid square IDs
    LA_overlaps =LA_overlaps_within_gird_squares.calc_LA_overlap_within_grid_square(grid_squares, LA_shapefile, weather_year)
    df_merged = heat_tech_distribution.merge_shapefile_FES_heating_tech_file(
        grid_squares, LA_overlaps, future_year, FES_year, FES_scenario, weather_year
    )
    total_dwellings = heat_tech_distribution.distribute_all_heating_techs_to_grids(
        df_merged, LA_overlaps, future_year, FES_year, FES_scenario, weather_year
    )
    pattern_profile_path = f"data/LA_UK/new_version/outputs/heat_demand_profiles_patterns/HD_heat_patterns_{weather_year}"
    scaled_heat_profiles = scaling_half_hourly_profiles_grid_sqs(
    pattern_profile_path,
    total_dwellings,
    weather_year,
    future_year,
    FES_year,
    FES_scenario,
    output_dir=None)

