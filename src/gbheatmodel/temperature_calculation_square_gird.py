import pandas as pd
import numpy as np
import atlite
import matplotlib.pyplot as plt
import xarray as xr
import FES_heat_supply_data
import geopandas as gpd
from geopandas import GeoDataFrame
from shapely.geometry import box
from shapely.geometry import Point
import logging
import warnings
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
from cartopy.crs import PlateCarree as plate
from matplotlib.gridspec import GridSpec
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
warnings.simplefilter("ignore")
logging.captureWarnings(False)
logging.basicConfig(level=logging.INFO)
from sklearn.cluster import DBSCAN
from pyproj import CRS
import tempfile
import os
import shutil
import calendar
import LA_overlaps_within_gird_squares
import LAs_aggregation


def air_temperature_calculation(cutout, year):
    '''Calculate the atlite grid square air temperature for a given year. If the air temperature file already exists, skip calculation and only check duplicates.'''
    
    air_temp_path = f'data/LA_UK/new_version/air_temp_new/air_temp_{year}.csv'
    
    # Check if the air temperature file already exists
    if os.path.exists(air_temp_path):
        print(f"✅ Air temperature data for {year} already exists. Loading existing file.")
        air_temp = pd.read_csv(air_temp_path, index_col=0)
    else:
        # Load site data
        site_path = f'data/LA_UK/new_version/grid_square_coord.csv'
        
        
        # Load the cutout
        cutout = atlite.Cutout(path=f'data/atlite/cutouts/uk-{year}.nc')
        sites = pd.read_csv(site_path)
        sites['capacity'] = 1.0
        sites.set_index('Grid_ID', inplace=True)
        nearest = cutout.data.sel({"x": sites.x.values, "y": sites.y.values}, "nearest").coords
        sites["x"] = nearest.get("x").values
        sites["y"] = nearest.get("y").values
        
        cells = cutout.grid
        cells_generation = sites.merge(cells, how="inner").rename(pd.Series(sites.index))
        
        # Remove duplicate grid squares
        cells_generation1 = cells_generation.drop_duplicates(subset=['y', 'x'], keep='first')
        
        layout = (
            xr.DataArray(cells_generation1.fillna(0.0).set_index(["y", "x"]).capacity.unstack())
        )
        
        air_temp = cutout.temperature(layout=layout, shapes=cells_generation1.geometry).to_pandas()
        print('✅ Air temperature calculated:', air_temp)
        
        # Save the calculated air temperature data
        air_temp.to_csv(air_temp_path)
    
        # # Check for duplicates
        # duplicates = air_temp[air_temp.duplicated(subset=['y', 'x'], keep=False)]
        # if not duplicates.empty:
        #     print(f"⚠️ Warning: Found {len(duplicates)} duplicate grid squares in air_temp.")
        #     print(duplicates.head())
        # else:
        #     print(f"✅ No duplicates found in air_temp.")
    
    return air_temp



def calc_grid_sq_average_day_temperature(day, year, grid_square_index):
    """
    Calculate the average day temperature for a given day (between 1 and 365 or 366), using historic year.
    """
    # read in the temperature data
    df = pd.read_csv('data/LA_UK/new_version/air_temp_new/air_temp_' + str(year) + '.csv', index_col=0)
    df.index = pd.to_datetime(df.index)
    df = df.loc[df.index.year == year]
    df = df.loc[df.index.dayofyear == day]
    df = df.loc[:, grid_square_index]

    # calculate the average temperature for the day
    average_day_temperature = df.mean()

    return average_day_temperature

def calc_grid_sq_year_average_day_temperature(year_historical, grid_square_index):
    # average day temp for each day
    # check number of days in year

    # read in the temperature data
    df = pd.read_csv('data/LA_UK/new_version/air_temp_new/air_temp_' + str(year_historical) + '.csv', index_col=0)
    df.index = pd.to_datetime(df.index)
    df = df.loc[df.index.year == year_historical]

    daysinyear = 365 + calendar.isleap(year_historical)
    day_temps = {}
    for day in range(1, daysinyear + 1):
    # for day in range(1, 4):
        df_temps = df.loc[df.index.dayofyear == day]
        df_temps = df_temps.loc[:, grid_square_index]
        # calculate the average temperature for the day
        day_temps[day] = df_temps.mean()

    day_temps = pd.Series(day_temps)
    day_temps.name = grid_square_index

    return day_temps

def save_all_grid_sq_year_average_day_temperature():
    # for year in range(2010, 2022 + 1):
    average_day_air_temp_path = f'data/LA_UK/new_version/air_temp_new/average_day_air_temp_{year}.csv'
    
    if not os.path.exists(average_day_air_temp_path):
        print(f"Processing {year}...")
        
        # Get a list of grid square indices
        df = pd.read_csv(f'data/LA_UK/new_version/air_temp_new/air_temp_{year}.csv', index_col=0)
        data = []
        for grid_square_index in df.columns:
            data.append(calc_grid_sq_year_average_day_temperature(year, grid_square_index))
        
        df_output = pd.DataFrame(data).T
        df_output.to_csv(average_day_air_temp_path)
        print(f"✅ Saved average day air temperature for {year}.")
    else:
        print(f"✅ Average day air temperature for {year} already exists. Skipping calculation.")

if __name__ == "__main__":
    years =list(range(2010, 2025))
    for year in years:
        _, grid_atlite = LAs_aggregation.prepare_cutouts_years(year)
        # prepare_cutouts_years(year)
        air_temperature_calculation(_,year)
        save_all_grid_sq_year_average_day_temperature()
    # year = 2010

    # _, grid_atlite = LAs_aggregation.prepare_cutouts_years(year)
    # LAs_aggregation.prepare_cutouts_years(year)
    # air_temperature_calculation(_,year)
    # save_all_LA_year_average_day_temperature()