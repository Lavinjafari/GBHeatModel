from __future__ import annotations

import os
import calendar
import logging
import warnings
from pathlib import Path

import atlite
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from geopandas import GeoDataFrame
from matplotlib.gridspec import GridSpec
from pandas.plotting import register_matplotlib_converters
from pyproj import CRS
from shapely.geometry import box, Point
from sklearn.cluster import DBSCAN

# cartopy imports (kept in case you use plotting elsewhere)
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
from cartopy.crs import PlateCarree as plate

# internal package imports
from .path import path_in_data, ensure_dir

register_matplotlib_converters()
warnings.simplefilter("ignore")
logging.captureWarnings(False)
logging.basicConfig(level=logging.INFO)


def air_temperature_calculation(cutout, year: int) -> pd.DataFrame:
    """
    Calculate the atlite grid square air temperature for a given year.

    If the air temperature file already exists, skip calculation and load it.
    """
    # e.g. data/air_temp/air_temp_2010.csv
    air_temp_path = path_in_data("air_temp", f"air_temp_{year}.csv")

    # Check if the air temperature file already exists
    if air_temp_path.exists():
        print(f"✅ Air temperature data for {year} already exists. Loading existing file.")
        air_temp = pd.read_csv(air_temp_path, index_col=0)
    else:
        print(f"▶ Calculating air temperature for {year}...")

        # Load site data
        site_path = path_in_data("grid_square_coord.csv")

        # Load the cutout (ignore the passed 'cutout' arg, kept only for backwards compatibility)
        cutout = atlite.Cutout(path=str(path_in_data("Atlite", f"uk-{year}.nc")))

        sites = pd.read_csv(site_path)
        sites["capacity"] = 1.0
        sites.set_index("Grid_ID", inplace=True)

        nearest = cutout.data.sel({"x": sites.x.values, "y": sites.y.values}, "nearest").coords
        sites["x"] = nearest.get("x").values
        sites["y"] = nearest.get("y").values

        cells = cutout.grid
        cells_generation = sites.merge(cells, how="inner").rename(pd.Series(sites.index))

        # Remove duplicate grid squares
        cells_generation1 = cells_generation.drop_duplicates(subset=["y", "x"], keep="first")

        layout = xr.DataArray(
            cells_generation1.fillna(0.0)
            .set_index(["y", "x"])
            .capacity.unstack()
        )

        air_temp = cutout.temperature(layout=layout, shapes=cells_generation1.geometry).to_pandas()
        print("✅ Air temperature calculated")

        # Ensure directory exists and save the calculated air temperature data
        ensure_dir(air_temp_path.parent)
        air_temp.to_csv(air_temp_path)
        print(f"💾 Saved air temperature to {air_temp_path}")

    return air_temp


def calc_grid_sq_average_day_temperature(
    day: int,
    year: int,
    grid_square_index: str,
) -> float:
    """
    Calculate the average day temperature for a given day (1–365/366) and grid square.
    """
    temp_path = path_in_data("air_temp", f"air_temp_{year}.csv")
    df = pd.read_csv(temp_path, index_col=0)
    df.index = pd.to_datetime(df.index)

    df = df.loc[df.index.year == year]
    df = df.loc[df.index.dayofyear == day]
    df = df.loc[:, grid_square_index]

    # calculate the average temperature for the day
    average_day_temperature = df.mean()

    return average_day_temperature


def calc_grid_sq_year_average_day_temperature(
    year_historical: int,
    grid_square_index: str,
) -> pd.Series:
    """
    Calculate average daily temperature for each day of a given year for one grid square.
    """
    temp_path = path_in_data("air_temp", f"air_temp_{year_historical}.csv")
    df = pd.read_csv(temp_path, index_col=0)
    df.index = pd.to_datetime(df.index)
    df = df.loc[df.index.year == year_historical]

    daysinyear = 365 + calendar.isleap(year_historical)
    day_temps: dict[int, float] = {}

    for day in range(1, daysinyear + 1):
        df_temps = df.loc[df.index.dayofyear == day]
        df_temps = df_temps.loc[:, grid_square_index]
        day_temps[day] = df_temps.mean()

    day_temps_series = pd.Series(day_temps)
    day_temps_series.name = grid_square_index

    return day_temps_series


def save_all_grid_sq_year_average_day_temperature(year: int) -> None:
    """
    Compute and save average daily air temperature for all grid squares in a given year.
    """
    average_day_air_temp_path = path_in_data("air_temp", f"average_day_air_temp_{year}.csv")

    if not average_day_air_temp_path.exists():
        print(f"Processing {year}...")

        # Get a list of grid square indices
        temp_path = path_in_data("air_temp", f"air_temp_{year}.csv")
        df = pd.read_csv(temp_path, index_col=0)

        data = []
        for grid_square_index in df.columns:
            data.append(calc_grid_sq_year_average_day_temperature(year, grid_square_index))

        df_output = pd.DataFrame(data).T

        ensure_dir(average_day_air_temp_path.parent)
        df_output.to_csv(average_day_air_temp_path)
        print(f"✅ Saved average day air temperature for {year}.")
    else:
        print(f"✅ Average day air temperature for {year} already exists. Skipping calculation.")


if __name__ == "__main__":
    years = list(range(2010, 2025))

    for year in years:
        print(f"\n=== Year {year} ===")
        cutout, grid_atlite = LAs_aggregation.prepare_cutouts_years(year)

        # Calculate (or load) half-hourly air temperature
        air_temperature_calculation(cutout, year)

        # Calculate and save average daily air temperature
        save_all_grid_sq_year_average_day_temperature(year)
