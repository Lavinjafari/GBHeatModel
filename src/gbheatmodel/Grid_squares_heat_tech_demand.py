import geopandas as gpd
import pandas as pd
import numpy as np
import atlite

import matplotlib.pyplot as plt
import heat_pattern
import FES_heat_supply_data
from shapely.geometry import Point
from sklearn.neighbors import NearestNeighbors
import FES_shapefile_LAs_matching
import LA_overlaps_within_gird_squares
import heat_tech_distribution

def calculate_heat_demand_for_grid_squares(LA_overlaps, weather_year, future_year, FES, scenario, LA_shapefile, grid_squares):
    
    # LA_shapefile = gpd.read_file(r'data\LA_UK\new_version\UK_LAs_Boundaries_files\LAs_shapefile_2021\LAD_DEC_2021_GB_BFC.shp')
   
    LA_overlaps = LA_overlaps_within_gird_squares.calc_LA_overlap_within_grid_square(grid_squares,
                                                                                     LA_shapefile,
                                                                                     weather_year)
    
    df_merged = heat_tech_distribution.merge_shapefile_FES_heating_tech_file(grid_squares, 
                                                                             LA_overlaps, 
                                                                             future_year,
                                                                             FES, 
                                                                             scenario,
                                                                             weather_year)
    
    df = heat_tech_distribution.distribute_all_heating_techs_to_grids(df_merged,
                                                                      LA_overlaps, 
                                                                      future_year,
                                                                      FES, 
                                                                      scenario,
                                                                      weather_year)

    # Identify heating tech columns
    non_tech = ['Grid_ID', 'Local_Authority', 'Year', 'Scenario', 'Sector']
    tech = df.select_dtypes(include='number').columns.difference(non_tech)
    if 'Grid_ID' in df.index.names:
        df = df.reset_index()


    # Aggregate demand
    grid_square_hd = df.groupby('Grid_ID')[tech].sum().reset_index()
    
    # Extract non-numeric metadata (first entry per Grid_ID)
    meta = df.groupby('Grid_ID')[['Year', 'Scenario', 'Sector']].first().reset_index()
    # Merge back
    grid_square_hd = pd.merge(grid_square_hd, meta, on='Grid_ID', how='left')
    meta_cols = ['Grid_ID', 'Year', 'Scenario', 'Sector']
    # Reorder columns in the output DataFrame
    tech_cols = [col for col in grid_square_hd.columns if col not in meta_cols]
    grid_square_hd = grid_square_hd[meta_cols + tech_cols]
    # Drop columns from index 17 onward
    grid_square_hd = grid_square_hd.iloc[:, :18]

    grid_square_hd.to_csv(r'data\LA_UK\new_version\data_call\scenario_alignment_data\heat_techs_distribution_grid_square.csv', index=False)

    return grid_square_hd




# def prepare_site_to_calc_air_temp(grid_square_hd):
#     # Only keep 'Grid_ID' column
#     df = grid_square_hd[['Grid_ID']].copy()

#     # Separate x and y coordinates from 'Grid_ID'
#     df[['x', 'y']] = df['Grid_ID'].str.split('_', expand=True).astype(float)
#     # df.set_index('Grid_ID', inplace=True)

#     # Save to CSV
#     df.to_csv(r'data\LA_UK\new_version\grid_square_coord.csv', index=False)

#     return df


if __name__ == "__main__":
    weather_year = 2024
    FES = '2022'
    future_year = 2050
    scenario = "LW"
    LA_shapefile = gpd.read_file(r'data\LA_UK\new_version\UK_LAs_Boundaries_files\LAs_shapefile_2021\LAD_DEC_2021_GB_BFC.shp')
    grid_squares =  gpd.read_file(r'data\LA_UK\new_version\data_call\UK_Atlite_Grid_sq.gpkg')
    LA_overlaps = LA_overlaps_within_gird_squares.calc_LA_overlap_within_grid_square(grid_squares, LA_shapefile, weather_year)

    # Calculate heat demand
    grid_square_hd = calculate_heat_demand_for_grid_squares(LA_overlaps, weather_year, future_year, FES, scenario, LA_shapefile, grid_squares)

    # Use heat demand result to prepare air temperature grid
    site = prepare_site_to_calc_air_temp(grid_square_hd)
