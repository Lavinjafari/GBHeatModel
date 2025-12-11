import pandas as pd
import numpy as np
import os
from gbheatmodel.path import path_in_data, ensure_dir

def electric_demand_for_heat(profiles, grid_sqs, df_ASHP, df_GSHP):
    """
    Calculate the electric demand for heat for all Grid Squares based on heat demand and heat pump efficiencies.
    
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
    df_ASHP.index = pd.to_datetime(df_ASHP.index)
    df_GSHP.index = pd.to_datetime(df_GSHP.index)
    for grid_id in grid_sqs:
        if grid_id not in profiles:
            print(f"⚠️ Skipping {grid_id}: not found in heat demand data.")
            continue
               
    
    # Loop through each grid_square
    # for grid_id in grid_sqs:
        # Extract the heat demand DataFrame for the current grid_square
        elec_hd_df = profiles[grid_id].loc[:, [
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
    
    
    return ed_grid_sqs