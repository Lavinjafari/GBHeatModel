import pandas as pd
import geopandas as gpd
import numpy as np
import FES_heat_supply_data
import pprint

import Grid_squares_heat_tech_demand
import LA_overlaps_within_gird_squares


def heat_demand_for_one_pattern_for_one_day(total_dwellings_pattern, heating_pattern, Td):
    """
    Calculate the heat demand for one day for a given number of dwellings, heating pattern, and average day temperature.
    """
    if heating_pattern == 'daytime':
        C = {'TBp':14.3, 'mp1':-5.39, 'cp1':88.8, 'mp2':-0.94, 'cp2':25.0, 'R2':0.97}
    elif heating_pattern == 'bi-modal':
        C = {'TBp':13.9, 'mp1':-5.22, 'cp1':83.7, 'mp2':-0.82, 'cp2':22.4, 'R2':0.97}
    elif heating_pattern == 'continuous':
        C = {'TBp':14.3, 'mp1':-6.18, 'cp1':102.6, 'mp2':-1.24, 'cp2':31.8, 'R2':0.98}
    elif heating_pattern == 'ASHP':
        C = {'TBp':14.3, 'mp1':-5.85, 'cp1':96.7, 'mp2':-1.1, 'cp2':28.7}
    elif heating_pattern == 'GSHP':
        C = {'TBp':14.3, 'mp1':-5.96, 'cp1':98.7, 'mp2':-1.15, 'cp2':29.8}

    # given a number of buildings using a heating pattern, calculate the heat demand using coefficients
    if Td < C['TBp']:
        HD = C['mp1'] * Td + C['cp1']
    elif Td >= C['TBp']:
        HD = C['mp2'] * Td + C['cp2']

    # calculate the heat demand for the given number of dwellings
    return HD * total_dwellings_pattern



def grid_sq_heat_pattern_totals(grid_squares, LA_shapefile, weather_year, future_year, FES, scenario):
    """
    Calculate the heat demand patterns for grid squares based on technology mixes.
    
    Parameters:
    -----------
    grid_squares : GeoDataFrame
        Grid squares data
    LA_shapefile : GeoDataFrame
        Local Authority boundaries data
    weather_year : int
        The weather year for calculations
    future_year : int
        The target year for the calculation
    FES : int
        The Future Energy Scenario year
    scenario : str
        The scenario name
        
    Returns:
    --------
    dict
        Dictionary mapping grid squares to their heat pattern distributions
    """
    # Get the grid square data
    try:
        grid_sq = pd.read_csv('data/LA_UK/new_version/air_temp_new/air_temp_2012.csv', index_col=0).columns
    except FileNotFoundError:
        raise FileNotFoundError("Could not find air temperature data file")
        
    # Get the heat demand data
    LA_overlaps = LA_overlaps_within_gird_squares.calc_LA_overlap_within_grid_square(
        grid_squares, LA_shapefile, weather_year
    )
    df = Grid_squares_heat_tech_demand.calculate_heat_demand_for_grid_squares(
        LA_overlaps, weather_year, future_year, FES, scenario, LA_shapefile, grid_squares
    )
    
    # Clean up column and index names more efficiently
    df.columns = df.columns.str.replace(r'stock ', '')
    index_replacements = {
        "Chiltern District": "Chiltern",
        "South Bucks District": "South Bucks",
        "Wycombe District": "Wycombe",
        "Aylesbury Vale District": "Aylesbury Vale"
    }

    # Convert index to Series, apply replacement, then assign back
    df.index = pd.Series(df.index).replace(index_replacements).values

    # Set index and validate
    df.set_index('Grid_ID', inplace=True)
    df.index = df.index.astype(str)
    
    # Validate that all grid squares exist in the heat demand data
    missing_squares = set(grid_sq) - set(df.index)
    if missing_squares:
        raise ValueError(f"Grid squares {missing_squares} not found in heat demand data")
    
    # Identify technology columns dynamically
    # non_tech_cols = ['Grid_ID', 'Local_Authority', 'Year', 'Scenario', 'Sector']
    list_of_tech = df.columns.values[3:18]
    # [col for col in df.columns if col not in non_tech_cols]
    
    # Ensure numeric columns are actually numeric
    df[list_of_tech] = df[list_of_tech].apply(pd.to_numeric, errors='coerce')
    # pd.DataFrame(list_of_tech, columns=["Technology"]).to_csv('data/LA_UK/new_version/list_of_tech.csv', index=False)

    # Define heating patterns
    heating_pattern_to_tech = {
        'ASHP': {'daytime': 30, 'bi-modal': 9, 'continuous': 61},
        'GSHP': {'daytime': 21, 'bi-modal': 5, 'continuous': 74},
        'Gas boiler': {'daytime': 46, 'bi-modal': 34, 'continuous': 20}
    }
    
    # Process each grid square
    dict_grid_sq = {}
    for grid_id in grid_sq:
        df_heat_pattern = pd.DataFrame(heating_pattern_to_tech)
        
        # Handle other technologies
        list_of_tech_ = [tech for tech in list_of_tech if tech not in 
                        ['ASHP', 'GSHP', 'Gas boiler', 'Electric storage']]
        
        # Set patterns for other technologies
        for tech in list_of_tech_:
            df_heat_pattern[tech] = {'daytime': 46, 'bi-modal': 34, 'continuous': 20}
            
        df_heat_pattern['Electric storage'] = {'daytime': 0, 'bi-modal': 0, 'continuous': 100}
        df_heat_pattern['Hybrid (ASHP + Electric resistive)'] = {
            'daytime': 46, 'bi-modal': 34, 'continuous': 20
        }
        
        # Calculate patterns
        df_heat_pattern = df_heat_pattern.T / 100
        for tech in list_of_tech:
            # Convert to numeric and handle any NA values
            tech_value = pd.to_numeric(df.loc[grid_id, tech], errors='coerce')
            # Handle both scalar and Series values
            if pd.isna(tech_value):
                print(f"Warning: NA value found for {tech} in grid square {grid_id}")
                tech_value = 0.0  # Replace NA value with 0.0
            df_heat_pattern.loc[tech] = tech_value * df_heat_pattern.loc[tech]
            
        dict_grid_sq[grid_id] = df_heat_pattern
        # Print totals for this grid square
        # print(f"\nHeat demand totals for grid square {grid_id}:")
        # print(dict_grid_sq[grid_id].sum(axis=1))
        print(dict_grid_sq)
    return dict_grid_sq

if __name__ == "__main__":
    weather_year = 2024
    FES = '2022'
    future_year = 2050
    scenario = "LW"
    grid_id = '-0.25_50.75'
 
    LA_shapefile = gpd.read_file(r'data\LA_UK\new_version\UK_LAs_Boundaries_files\LAs_shapefile_2021\LAD_DEC_2021_GB_BFC.shp')
    

    grid_squares =  gpd.read_file(r'data\LA_UK\new_version\data_call\UK_Atlite_Grid_sq.gpkg')
    # Calculate heat demand
    grid_sq_heat_pattern_total = grid_sq_heat_pattern_totals(grid_squares, LA_shapefile, weather_year, future_year, FES, scenario)
    grid_totals = grid_sq_heat_pattern_total['-0.25_50.75'].sum(axis=1)
    print(grid_totals)
    
    