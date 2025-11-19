import pandas as pd
import numpy as np
import os

def electric_demand_for_heat(scaled_profiles_dict, grid_sqs, df_ASHP, df_GSHP):
    """
    Calculate the electric demand for heat for all LAs
    
    Parameters:
    hd_grid_sqs (dict): Dictionary of heat demand DataFrames for all grid_squares
    grid_sqs (list): List of grid_squares(with defined IDs including longitude and latitude(x_y))
    df_ASHP (DataFrame): DataFrame with ASHP efficiency data
    df_GSHP (DataFrame): DataFrame with GSHP efficiency data
    
    Returns:
    dict: Dictionary with electric demand for heat for each grid_square
    """
    
    # Initialize an empty dictionary to store electric demand for each grid_square
    ed_grid_sqs = {}
    for grid_id in grid_sqs:
        if grid_id not in scaled_profiles_dict:
            print(f"⚠️ Skipping {grid_id}: not found in heat demand data.")
            continue
        df_ASHP.index = pd.to_datetime(df_ASHP.index)
        df_GSHP.index = pd.to_datetime(df_GSHP.index)       
    
    # Loop through each grid_square
    # for grid_id in grid_sqs:
        # Extract the heat demand DataFrame for the current grid_square
        elec_hd_df = scaled_profiles_dict[grid_id].loc[:, [
            'ASHP', 'GSHP', 
            'Hybrid (ASHP + BioLPG boiler)', 
            'Hybrid (ASHP + Hydrogen boiler)', 
            'Hybrid (ASHP + Electric resistive)'
            ]].copy()

        # print("HD index head:", elec_hd_df.index[:3])
        # print("COP index head:", df_ASHP[grid_id].index[:3])

        # Calculate electric demand for ASHP
        elec_hd_df['ASHP Elec'] = elec_hd_df['ASHP'] / df_ASHP[grid_id]
        
        # Calculate electric demand for GSHP
        elec_hd_df['GSHP Elec'] = elec_hd_df['GSHP'] / df_GSHP[grid_id]
        
        # Calculate electric demand for hybrid systems
        elec_hd_df['Hybrid (ASHP + BioLPG boiler) Elec'] = 0.70 * elec_hd_df['Hybrid (ASHP + BioLPG boiler)'] / df_ASHP[grid_id]
        elec_hd_df['Hybrid (ASHP + Hydrogen boiler) Elec'] = 0.90 * elec_hd_df['Hybrid (ASHP + Hydrogen boiler)'] / df_ASHP[grid_id]
        elec_hd_df['Hybrid (ASHP + Electric resistive) Elec'] = 0.90 * elec_hd_df['Hybrid (ASHP + Electric resistive)'] / df_ASHP[grid_id] + 0.10 * elec_hd_df['Hybrid (ASHP + Electric resistive)']

        # Store the electric demand DataFrame for the current grid_square in the dictionary
        ed_grid_sqs[grid_id] = elec_hd_df[['ASHP Elec', 'GSHP Elec', 'Hybrid (ASHP + BioLPG boiler) Elec', 'Hybrid (ASHP + Hydrogen boiler) Elec', 'Hybrid (ASHP + Electric resistive) Elec']]
    
    # Return the dictionary with electric demand for all grid_squares
    # print(ed_grid_sqs[grid_id])
    return ed_grid_sqs

if __name__ == '__main__':
    weather_year = 2012
    future_year = 2050
    FES_year = '2022'
    FES_scenario = 'LW'
  

    # Get grid square IDs
    grid_sqs = pd.read_csv('data/LA_UK/new_version/air_temp_new/air_temp_2012.csv', index_col=0).columns

    # Load heat demand data for all grid squares
    folder = rf"data\LA_UK\new_version\outputs\heating_profiles\{FES_year}_{FES_scenario}_{future_year}"
    grid_id = '-0.25_50.75'
    file_name = f"half_hourly_heat_profile_{grid_id}_{FES_year}_{FES_scenario}_{future_year}.csv"
    file_path = os.path.join(folder, file_name)

    if os.path.exists(file_path):
        hd_df = pd.read_csv(file_path, index_col=0)
        hd_df.index = pd.to_datetime(hd_df.index)
        hd_grid_sqs = {grid_id: hd_df}
    else:
        print(f"⚠️ File not found: {file_path}")
        hd_grid_sqs = {}

    # Load COP profiles
    df_ASHP = pd.read_csv('data/LA_UK/new_version/outputs/COP_Profiles/ASHP_very good_2012_2050.csv', index_col=0)
    df_GSHP = pd.read_csv('data/LA_UK/new_version/outputs/COP_Profiles/GSHP_very good_2012_2050.csv', index_col=0)

    # ⚠️ Do NOT overwrite hd_grid_sqs here
    # hd_grid_sqs = pd.read_csv(file_path, index_col=0)  # REMOVE THIS LINE

    # Compute electric demand
    ed_grid_sqs = electric_demand_for_heat(hd_grid_sqs, [grid_id], df_ASHP, df_GSHP)
  


    # Save the electric demand data
    print(ed_grid_sqs)
    
    # output_folder = 'data/LA_UK/new_version/outputs/elec_for_heat_demand_profiles'
    # df = pd.DataFrame.from_dict(ed_grid_sqs)
    # df.to_csv(os.path.join(output_folder, f"elec_demand_{grid_id}_{FES_year}_{FES_scenario}_{future_year}.csv"))
    


