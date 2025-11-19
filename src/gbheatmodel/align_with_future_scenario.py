import pandas as pd
import os


def scale_FES_dwellings(FES_data, total_dwelling_new):
    """
    Clean and scale the FES data to match the total dwellings of a new scenario.
    Assumes technology columns contain number of dwellings (one tech per dwelling).

    Parameters:
    - FES_data: DataFrame containing Grid_ID, Year, Scenario, Sector, and tech columns.
    - total_dwelling_new: Total number of dwellings in the new scenario.

    Returns:
    - scaled_df: DataFrame with 'Grid_ID' and scaled 'total_dwellings' columns only.
    """

    # Identify technology columns (numeric but not metadata)
    meta_cols = ['Year', 'Scenario', 'Sector']
    tech_cols = [col for col in FES_data.columns if col not in meta_cols and pd.api.types.is_numeric_dtype(FES_data[col])]

    # Calculate total dwellings per grid (sum of tech columns)
    FES_df = FES_data.copy()
    FES_df['Grid_ID'] = FES_data['Grid_ID']
    FES_df['total_dwellings'] = FES_df[tech_cols].sum(axis=1)
    # print(FES_df.head())

    # Calculate total FES dwellings
    total_FES_dwellings = FES_df['total_dwellings'].sum()
    # print("Total FES dwellings:", total_FES_dwellings)

    # Compute scaling factor
    scaling_factor = total_dwelling_new / total_FES_dwellings

    # Scale only the total_dwellings column
    FES_df['total_dwellings'] = FES_df['total_dwellings'] * scaling_factor
    new_scenario_dwellings_dist= FES_df[['Grid_ID', 'total_dwellings']]
    # sum the total_dwellings column
    total_dwellings_sum = new_scenario_dwellings_dist['total_dwellings'].sum()
    # print("Total dwellings sum:", total_dwellings_sum)
    # print(new_scenario_dwellings_dist.head())


    # Return only Grid_ID and scaled total_dwellings
    return new_scenario_dwellings_dist


def assign_tech_shares(new_scenario_dwellings_dist, type_of_techs,share_of_techs):
    """
    Assign technology shares to each grid square based on scenario assumptions.
    Important Note: In this model, the total number of dwellings in each grid square is equal to the total number of dwellings (one tech = one dwelling).

    Parameters:
    - new_scenario_dwellings_dist: DataFrame shows the total number of dwellings for each grid square based on dwelling scaling factor of FES and new scenario.
    - type_of_techs: List of technology names in the new scenario, e.g., ['ASHP', 'GSHP']
    - share_of_techs: List of technology shares assumed in the new scenario, e.g., [0.75, 0.25]

    Returns:
    - grid_square_hd: DataFrame with 'Grid_ID' and columns for each tech showing dwelling counts within each grid square ready to use for calculating half-hourly heat demand.
    """
    if not (len(type_of_techs) == len(share_of_techs)):
        raise ValueError("type_of_techs and share_of_techs must be the same length.")

    if abs(sum(share_of_techs) - 1.0) > 1e-5:
        raise ValueError("Shares must sum to 1.0")

    grid_square_hd = new_scenario_dwellings_dist[['Grid_ID']].copy()

    for tech, share in zip(type_of_techs, share_of_techs):
        grid_square_hd[tech] = new_scenario_dwellings_dist['total_dwellings'] * share

    return grid_square_hd

    
if __name__ == "__main__":
    FES_data = pd.read_csv(r'data\LA_UK\new_version\data_call\scenario_alignment_data\heat_techs_distribution_grid_square.csv')
    total_dwelling_new = 25.8e6
    new_scenario_dwellings_dist = scale_FES_dwellings(FES_data, total_dwelling_new)
    new_scenario_dwellings_dist.to_csv(r'data\LA_UK\new_version\data_call\scenario_alignment_data\heat_techs_distribution_grid_square_scaled.csv', index=False)
    type_of_techs = ['ASHP', 'GSHP']
    share_of_techs = [0.75, 0.25]
    grid_square_hd = assign_tech_shares(new_scenario_dwellings_dist, type_of_techs, share_of_techs)
    grid_square_hd.to_csv(r'data\LA_UK\new_version\data_call\scenario_alignment_data\hd_distribution_new_scenario.csv', index=False)
    total = grid_square_hd[['ASHP', 'GSHP']].sum()
    print("ASHP share:", total['ASHP'] / total.sum())
    print("GSHP share:", total['GSHP'] / total.sum())

