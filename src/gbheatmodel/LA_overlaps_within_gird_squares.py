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



def calc_LA_overlap_within_grid_square(grid_squares, LA_shapefile, weather_year):
    
    
    # LA_shapefile = gpd.read_file(r'data\LA_UK\new_version\UK_LAs_Boundaries_files\LAs_shapefile_2021\LAD_DEC_2021_GB_BFC.shp')
    # grid_squares = gpd.read_file(r'data\LA_UK\new_version\data_call\UK_Atlite_Grid_sq.csv')
    # Convert grid_squares to match LA_shapefile CRS (EPSG:27700)
    if grid_squares.crs != LA_shapefile.crs:
        grid_squares = grid_squares.to_crs(LA_shapefile.crs)
       
    # LAs_overlaps: how much of each LA overlaps each grid square?
    LAs_overlaps = gpd.overlay(grid_squares,
                     LA_shapefile,
                     how='intersection')
   
    LAs_overlaps["overlap_area"] = LAs_overlaps.geometry.area
    LAs_overlaps["LA_area"] = LAs_overlaps.groupby("LAD21NM")["overlap_area"].transform("sum")
    LAs_overlaps["overlap_percentage"] = LAs_overlaps["overlap_area"] / LAs_overlaps["LA_area"] * 100
    LAs_overlaps["grid_id"] = LAs_overlaps.apply(lambda row: f"{row['x']}_{row['y']}", axis=1)
   
   
# # Plot
    # fig, ax = plt.subplots(figsize=(10, 10))
    # LA_shapefile.plot(ax=ax,
    #                   color="lightgrey",
    #                   edgecolor="black",
    #                   alpha=0.5, 
    #                   label="Local Authorities")
    # grid_squares.plot(ax=ax,
    #               color="none",
    #               edgecolor="red",
    #               linestyle="--",
    #               label="Grid Squares")
    # LAs_overlaps.plot(ax=ax,
    #         color="blue",
    #         alpha=0.5, 
    #         label="Overlap Regions")
    
    # plt.legend()
    # plt.title("Overlap Between Local Authorities and Grid Squares")
    # plt.show()
    # Selecting only useful columns and renaming them for clarity
    # LAs_overlaps.drop(columns=["CTYUA24CD"], inplace=True)
# clean the data
    LAs_overlaps.drop(columns=["LAD21NMW"], inplace=True)
    LAs_overlaps.drop(columns=["BNG_E"], inplace=True)
    LAs_overlaps.drop(columns=["BNG_N"], inplace=True)
    LAs_overlaps.drop(columns=["GlobalID"], inplace=True)
    LAs_overlaps.drop(columns=["geometry"], inplace=True)
    LAs_overlaps.rename(columns={"LAD21NM": "Local_Authority",
                       'LAD21CD': 'LA_Code',
                       "x": "grid_x",
                       "y": "grid_y",
                       'LONG': 'long',
                       'LAT': 'lat',
                       'grid_id': 'Grid_ID'},
                        inplace=True
                        )
    LAs_overlaps.set_index('Grid_ID', inplace=True)
    LAs_overlaps.to_csv(r'C:\Users\s2583817\OneDrive - University of Edinburgh\Documents\Projects\PhD_Project\Python\PyPSA-GB_Domestic_Heat\data\LA_UK\new_version\perc_LAs_in_grid_square.csv')
    # # print(LAs_overlaps)
    return LAs_overlaps


if __name__ == "__main__":
    weather_year = 2024
    FES = '2022'
    future_year = 2050
    scenario = "LW"
    LA_shapefile = gpd.read_file(r'data\LA_UK\new_version\UK_LAs_Boundaries_files\LAs_shapefile_2021\LAD_DEC_2021_GB_BFC.shp')
    # print(LA_shapefile.info())
    grid_squares =  gpd.read_file(r'data\LA_UK\new_version\data_call\UK_Atlite_Grid_sq.gpkg')
    
    # Calculate overlaps and percentages
    LAs_overlaps = calc_LA_overlap_within_grid_square(grid_squares, LA_shapefile, weather_year)