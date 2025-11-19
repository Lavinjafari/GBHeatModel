import os
import pandas as pd
import tech_half_hourly_profile
import align_with_future_scenario




# def calculate_half_hourly_profiles_custom_scenario(
#     pattern_profile_path,
#     total_dwellings,
#     weather_year,
#     future_year,
#     scenario_name,
#     output_dir= None,
#     insulation_improvement= 1.0
# ):
#     """
#     Calculates half-hourly heat demand per grid square based on user-defined scenario assumptions.

#     Parameters
#     ----------
#     pattern_profile_path : str
#         Directory path to the base heat demand profile CSVs per grid square.
#     total_dwellings : pd.DataFrame
#         DataFrame with columns: 'Grid_ID', technology types, and dwellings per tech per grid square.
#     weather_year : int
#         Year corresponding to the temperature and usage pattern profile (e.g., 2012).
#     future_year : int
#         Year for which to model heating demand (e.g., 2035).
#     scenario_name : str
#         Name of the custom scenario (used in file naming and folders).
#     output_dir : str, optional
#         Where to save the output files. If None, default path is used.
#     insulation_improvement : float, optional
#         Factor to scale heat demand due to building insulation improvement (default = 1.0, i.e., no change).

#     Returns
#     -------
#     dict
#         Dictionary mapping each Grid_ID to a DataFrame of 17520 half-hourly values per technology.
#     """

#     # Prepare input DataFrame
#     total_dwellings = align_with_future_scenario.assign_tech_shares(new_scenario_dwellings_dist, type_of_techs,share_of_techs)
#     total_dwellings = total_dwellings.copy()
#     total_dwellings['Grid_ID'] = total_dwellings['Grid_ID'].astype(str).str.strip()
#     total_dwellings.set_index('Grid_ID', inplace=True)

#     # Load grid square list from air temperature data
#     air_temp_path = f'data/LA_UK/new_version/air_temp_new/air_temp_{weather_year}.csv'
#     air_temp_df = pd.read_csv(air_temp_path, index_col=0)
#     grid_sqs = [str(gid).strip() for gid in air_temp_df.columns]

#     # Load base pattern coefficients
#     base_pattern = tech_half_hourly_profile.base_heat_pattern_per_technology()

#     # Setup output directory
#     if output_dir is None:
#         output_dir = f"data/LA_UK/new_version/outputs/heating_profiles_custom/{weather_year}_{scenario_name}_{future_year}"
#     os.makedirs(output_dir, exist_ok=True)

#     existing_profiles_dict = {}
#     all_exist = True

#     # Check for existing files
#     for grid_id in grid_sqs:
#         file_path = os.path.join(output_dir, f"half_hourly_heat_profile_{grid_id}_{scenario_name}_{weather_year}_{future_year}.csv")
#         if os.path.exists(file_path):
#             df = pd.read_csv(file_path, index_col=0)
#             df.index = pd.to_datetime(df.index)
#             existing_profiles_dict[grid_id] = df
#         else:
#             all_exist = False
#             break

#     if all_exist:
#         print("✅ All custom scenario heating profiles already exist. Loaded from disk.")
#         return existing_profiles_dict

#     # Compute missing profiles
#     scaled_profiles_dict = {}

#     for grid_id in grid_sqs:
#         if grid_id not in total_dwellings.index:
#             print(f"⚠️ Skipping {grid_id} — no dwelling data in custom scenario.")
#             continue

#         pattern_file = os.path.join(pattern_profile_path, f"({grid_id})_{weather_year}.csv")
#         if not os.path.exists(pattern_file):
#             print(f"⚠️ Skipping {grid_id} — pattern file missing.")
#             continue

#         try:
#             pattern_profile = pd.read_csv(pattern_file, index_col=0)
#         except Exception as e:
#             print(f"⚠️ Error loading pattern for {grid_id}: {e}")
#             continue

#         tech_dwellings = total_dwellings.loc[grid_id]
#         if isinstance(tech_dwellings, pd.DataFrame):
#             tech_dwellings = tech_dwellings.iloc[0]

#         data = {}
#         for tech in base_pattern.index:
#             if tech not in tech_dwellings or tech_dwellings[tech] == 0:
#                 continue
#             # print(f"{grid_id} → {tech}: {tech_dwellings[tech]}")

#             profile = (
#                 pattern_profile['daytime'].values * float(base_pattern.loc[tech, 'daytime']) +
#                 pattern_profile['bi-modal'].values * float(base_pattern.loc[tech, 'bi-modal']) +
#                 pattern_profile['continuous'].values * float(base_pattern.loc[tech, 'continuous'])
#             ) * float(tech_dwellings[tech]) * insulation_improvement  # 🔁 Apply insulation factor
#             data[tech] = profile

#         if not data:
#             print(f"⚠️ Skipping {grid_id} — no tech shares found.")
#             continue

#         scaled_profile = pd.DataFrame.from_dict(data, orient='columns')
#         scaled_profile.index = pd.date_range(start=f'{future_year}-01-01', periods=17520, freq='30min')

#         output_path = os.path.join(output_dir, f"half_hourly_HD_{grid_id}_{scenario_name}_{weather_year}_{future_year}.csv")
#         scaled_profile.to_csv(output_path)
#         print(f"✅ Saved: {output_path}")

#         scaled_profiles_dict[grid_id] = scaled_profile

#     return scaled_profiles_dict
def calculate_half_hourly_profiles_rhpp_shared(
    pattern_profile_path,
    total_dwellings,
    weather_year,
    future_year,
    scenario_name,
    output_dir=None,
    insulation_improvement=1.0
):
    """
    Calculates half-hourly heat demand per grid square using RHPP-based pattern shares (Watson et al. base case).

    Parameters
    ----------
    pattern_profile_path : str
        Path to heat demand pattern CSVs for each grid square.
    total_dwellings : pd.DataFrame
        DataFrame with columns: 'Grid_ID' and 'dwellings' (total per grid square).
    weather_year : int
        Historical weather year used to calculate temperature-driven demand (e.g., 2010).
    future_year : int
        Year to assign to the simulation results (for naming).
    scenario_name : str
        Name for output files (e.g., 'Watson_model').
    output_dir : str, optional
        Path to save outputs. If None, a default path is used.
    insulation_improvement : float, optional
        Demand reduction factor due to improved insulation (1.0 = no change).

    Returns
    -------
    dict
        Mapping from Grid_ID to half-hourly DataFrames.
    """
    # RHPP pattern shares from Watson et al. (2021)
    rhpp_shares = {'daytime': 0.28, 'bi-modal': 0.08, 'continuous': 0.64}

    # Prepare input
    total_dwellings = align_with_future_scenario.scale_FES_dwellings(FES_data, total_dwelling_new)
    total_dwellings = total_dwellings.copy()
    total_dwellings['Grid_ID'] = total_dwellings['Grid_ID'].astype(str).str.strip()
    total_dwellings.set_index('Grid_ID', inplace=True)

    # Load list of grid squares from weather data
    air_temp_path = f'data/LA_UK/new_version/air_temp_new/air_temp_{weather_year}.csv'
    air_temp_df = pd.read_csv(air_temp_path, index_col=0)
    grid_sqs = [str(gid).strip() for gid in air_temp_df.columns]

    # Set output directory
    if output_dir is None:
        output_dir = f"data/LA_UK/new_version/outputs/heating_profiles_custom/{weather_year}_{scenario_name}_{future_year}"
    os.makedirs(output_dir, exist_ok=True)

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
            print(f"❌ Error loading pattern for {grid_id}: {e}")
            continue

        # Weighted RHPP profile
        rhpp_weighted_profile = (
            pattern_profile['daytime'].values * rhpp_shares['daytime'] +
            pattern_profile['bi-modal'].values * rhpp_shares['bi-modal'] +
            pattern_profile['continuous'].values * rhpp_shares['continuous']
        )

        # Multiply by total dwellings and insulation factor
        num_dwellings = total_dwellings.loc[grid_id]['total_dwellings']
        final_profile = rhpp_weighted_profile * num_dwellings * insulation_improvement

        df = pd.DataFrame({'heat_demand': final_profile})
        df.index = pd.date_range(start=f'{future_year}-01-01', periods=17520, freq='30min')

        output_path = os.path.join(output_dir, f"half_hourly_HD_{grid_id}_{scenario_name}_{weather_year}_{future_year}.csv")
        df.to_csv(output_path)
        print(f"✅ Saved: {output_path}")

        scaled_profiles_dict[grid_id] = df

    return scaled_profiles_dict






if __name__ == "__main__":
    FES_data = pd.read_csv(r'data\LA_UK\new_version\data_call\scenario_alignment_data\heat_techs_distribution_grid_square.csv')
    total_dwelling_new = 25.8e6
    # new_scenario_dwellings_dist = align_with_future_scenario.scale_FES_dwellings(FES_data, total_dwelling_new)
    # type_of_techs = ['ASHP', 'GSHP']
    # share_of_techs = [0.75, 0.25]
    # total_dwellings = align_with_future_scenario.assign_tech_shares(new_scenario_dwellings_dist, type_of_techs, share_of_techs)
    total_dwellings = align_with_future_scenario.scale_FES_dwellings(FES_data, total_dwelling_new)
    weather_year = 2010
    future_year = 2050
    scenario_name = 'Watson_model'
    output_dir = f"data/LA_UK/new_version/outputs/heating_profiles_custom/{weather_year}_{scenario_name}_{future_year}"
    insulation_improvement = 1
    pattern_profile_path = f"data/LA_UK/new_version/outputs/heat_demand_profiles_patterns/HD_heat_patterns_{weather_year}"
    calculate_half_hourly_profiles_rhpp_shared(pattern_profile_path, total_dwellings, weather_year, future_year, scenario_name, output_dir, insulation_improvement)
    print(total_dwellings[['ASHP', 'GSHP']].sum())


