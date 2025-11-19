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


def merge_shapefile_FES_heating_tech_file(grid_squares, LA_overlaps, future_year, FES, scenario, weather_year):
    """
    merging shapefile and FES data for futhur calculation.
    """
    
    # LA_shapefile = gpd.read_file(r'data\LA_UK\new_version\UK_LAs_Boundaries_files\LAs_shapefile_2021\LAD_DEC_2021_GB_BFC.shp')
    # grid_squares = gpd.read_file(r'data\LA_UK\new_version\data_call\UK_Atlite_Grid_sq.csv')
    # LA_overlaps = LA_overlaps_within_gird_squares.calc_LA_overlap_within_grid_square(grid_squares, LA_shapefile, weather_year)
    
    df_FES = FES_heat_supply_data.year_FES_heat_supply(future_year, FES, scenario)
    df = FES_shapefile_LAs_matching.match_FES_and_shapefile_LAs(df_FES, future_year, FES, scenario)
    # Get list of heat technologies
    list_of_tech = df.columns.values[4:18]
    
    LA_overlaps['Local_Authority'] = LA_overlaps['Local_Authority'].astype(str)
    df.index = df.index.astype(str)
    # Remove rows where Local_Authority is None or NaN
    LA_overlaps = LA_overlaps[
        LA_overlaps['Local_Authority'].notna() &
        (LA_overlaps['Local_Authority'] != 'None')
    ]

    # Strip and title-case for consistency
    LA_overlaps['Local_Authority'] =LA_overlaps['Local_Authority'].str.strip().str.title()

    # Ensure df index is also title-cased
    df.index = df.index.str.strip().str.title()
    print("Sample FES LAs:", df.index.tolist()[:10])
    print("Sample Grid LAs:", LA_overlaps['Local_Authority'].unique()[:10])

    # Now merge the two DataFrames
    df_merged = pd.merge(
        LA_overlaps,
        df,
        left_on='Local_Authority',
        right_index=True,
        how='left',
        validate='m:1'  # Many grid squares to one LA
    )
    df_merged["Grid_ID"] = df_merged.apply(lambda row: f"{row['grid_x']}_{row['grid_y']}", axis=1)
    df_merged.set_index('Grid_ID', inplace=True)
    
    df_merged.to_csv(r'C:\Users\s2583817\OneDrive - University of Edinburgh\Documents\Projects\PhD_Project\Python\PyPSA-GB_Domestic_Heat\data\LA_UK\new_version\merged_FES_heat_tech.csv', index=False)
    
    
    return df_merged


# Define the function to distribute all heating technologies for each LA
def distribute_all_heating_techs_to_grids(df,LA_overlaps, future_year, FES, scenario, weather_year):
    
    LA_shapefile = gpd.read_file(r'data\LA_UK\new_version\UK_LAs_Boundaries_files\LAs_shapefile_2021\LAD_DEC_2021_GB_BFC.shp')
    grid_squares =  gpd.read_file(r'data\LA_UK\new_version\data_call\UK_Atlite_Grid_sq.gpkg')
    LA_overlaps = LA_overlaps_within_gird_squares.calc_LA_overlap_within_grid_square(grid_squares, 
                                                                                     LA_shapefile,
                                                                                     weather_year)
    # Extract all tech columns based on position
    
    df_merged = merge_shapefile_FES_heating_tech_file(grid_squares, 
                                                      LA_overlaps, 
                                                      future_year, 
                                                      FES, 
                                                      scenario, 
                                                      weather_year)
    
    list_of_tech = df_merged.columns[13:]  # assuming techs start from column 12
    distributed_heat_tech = []
    # for LA in df_merged['Local_Authority'].unique():
    #     df_LA = df_merged[df_merged['Local_Authority'] == LA].copy()
    #     print(f"{LA}: rows = {len(df_LA)}, tech_total = {df_LA[list_of_tech].iloc[0].sum()}")


    for LA in df_merged['Local_Authority'].unique():
        df_LA = df_merged[df_merged['Local_Authority'] == LA].copy()
        perc_sum = df_LA['overlap_percentage'].sum()

        if perc_sum == 0:
            continue  # skip if no overlap
        
        df_LA = df_LA.reset_index()  

        for tech in list_of_tech:
            tech_total = df_LA[tech].iloc[0]
            # coeff = tech_total / perc_sum
            # df_LA[tech] = df_LA['overlap_percentage'] * coeff
            # Normalize overlap_percentage so total sums to 1.0
            df_LA['normalized_overlap'] = df_LA['overlap_percentage'] / df_LA['overlap_percentage'].sum()
            df_LA[tech] = df_LA['normalized_overlap'] * tech_total

            # if 'geometry' in df_LA.columns:
            #     # The heat demand is normalized per square meter, making the result an intensity (demand per area) instead of absolute value.
            #     df_LA[tech] = (df_LA['overlap_percentage'] * coeff) / df_LA['geometry'].area
        
        
        # Keep only relevant columns: Grid identifiers + distributed results
        keep_cols = ['Grid_ID', 'Local_Authority', 'Year', 'Scenario', 'Sector'] + [tech for tech in list_of_tech]
        distributed_heat_tech.append(df_LA[keep_cols])
    df = pd.concat(distributed_heat_tech, ignore_index=True)
    df.to_csv(r'data\LA_UK\new_version\distributed_heat_tech.csv', index=False)

    return df




if __name__ == "__main__":
    weather_year = 2010
    FES = '2022'
    future_year = 2050
    scenario = "LW"
    LA_shapefile = gpd.read_file(r'data\LA_UK\new_version\UK_LAs_Boundaries_files\LAs_shapefile_2021\LAD_DEC_2021_GB_BFC.shp')
    # print(LA_shapefile.info())
    grid_squares =  gpd.read_file(r'data\LA_UK\new_version\data_call\UK_Atlite_Grid_sq.gpkg')
    LA_overlaps = LA_overlaps_within_gird_squares.calc_LA_overlap_within_grid_square(grid_squares, LA_shapefile, weather_year)

    # Merge shapefile with FES heating technology data
    df = merge_shapefile_FES_heating_tech_file(grid_squares, LA_overlaps, future_year, FES, scenario, weather_year)

    # Distribute heating technologies to grid squares
    distributed_heat_tech_df = distribute_all_heating_techs_to_grids(df,LA_overlaps, future_year, FES, scenario, weather_year)
    
    # # Validate mass conservation across all LAs and techs
    # non_tech_cols = ['Year', 'Scenario', 'Sector', 'Grid_ID', 'Local_Authority', 'LA_Code', 'grid_x', 'grid_y', 'lat', 'long']
    # techs = [col for col in df.columns if col not in non_tech_cols and df[col].dtype in ['float64', 'int64']]


    # print("\n=== 🔍 Checking Mass Conservation ===")
    # for la in df.index.unique():
    #     for tech in techs:
    #         if tech not in df.columns or tech not in distributed_heat_tech_df.columns:
    #             continue  # skip if column doesn't exist
    #         original = df.loc[la, tech]
    #         distributed = distributed_heat_tech_df[distributed_heat_tech_df['Local_Authority'] == la][tech].sum()
    #         if not pd.isna(original) and abs(original - distributed) > 1e-3:
    #             print(f"⚠️ {tech} in {la} mismatch: Original={original:.2f}, Distributed={distributed:.2f}")
