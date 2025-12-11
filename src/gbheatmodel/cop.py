import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from calendar import isleap
from .path import path_in_data, ensure_dir

def average_day_cop_for_heat_pump(heat_pump_type, performance_level, Td):
    """
    Calculate the average COP over a day for a heat pump given the type, performance level and average day temperature
    uses https://doi.org/10.1016/j.enbuild.2023.112917
    """
    if heat_pump_type == 'ASHP':
        if performance_level == 'current':
            C = {'TBp':8.2, 'm1':0.060, 'c1':2.07, 'm2':-0.088, 'c2':3.29, 'R2':0.78}
        elif performance_level == 'good':
            C = {'TBp':8.6, 'm1':0.070, 'c1':2.46, 'm2':-0.120, 'c2':4.10, 'R2':0.74}
        elif performance_level == 'very good':
            C = {'TBp':9.5, 'm1':0.078, 'c1':2.83, 'm2':-0.147, 'c2':4.97, 'R2':0.53}
    elif heat_pump_type == 'GSHP':
        if performance_level == 'current':
            C = {'TBp':5.0, 'm1':0.000, 'c1':2.50, 'm2':-0.053, 'c2':2.77, 'R2':0.71}
        elif performance_level == 'good':
            C = {'TBp':5.2, 'm1':0.000, 'c1':3.01, 'm2':-0.059, 'c2':3.32, 'R2':0.54}
        elif performance_level == 'very good':
            C = {'TBp':12.6, 'm1':0.00, 'c1':3.49, 'm2':-0.087, 'c2':4.58, 'R2':0.11}

    # calculate the COP using coefficients
    if Td < C['TBp']:
        COP = C['m1'] * Td + C['c1']
    elif Td >= C['TBp']:
        COP = C['m2'] * Td + C['c2']

    return COP


def day_cop_for_year_grid_sq(heat_pump_type, performance_level, future_year, weather_year):
    """
    Create a half-hourly COP profile (one year) for each grid square, based on
    average daily air temperature per grid square.

    Output:
        CSV at: data/outputs/COP_Profiles/<heat_pump_type>_<performance_level>_<weather_year>_<future_year>.csv
    """

    # --- 1. Input: daily average air temperatures for the weather year ---
    avg_air_temp_path = path_in_data(
        "air_temp",
        f"average_day_air_temp_{weather_year}.csv",
    )
    air_temp_daily = pd.read_csv(avg_air_temp_path, index_col=0)

    # Make sure the index is a proper daily DatetimeIndex
    air_temp_daily.index = pd.date_range(
        start=f"{weather_year}-01-01",
        periods=len(air_temp_daily),
        freq="D",
    )

    # If future year is NOT leap, drop 29 Feb from the weather-year series (if present)
    if not isleap(future_year):
        air_temp_daily = air_temp_daily[
            ~((air_temp_daily.index.month == 2) & (air_temp_daily.index.day == 29))
        ]

    # Number of days we are actually using
    n_days = len(air_temp_daily)

    # --- 2. Prepare output path / directory ---
    out_dir = path_in_data("outputs", "COP_Profiles")
    ensure_dir(out_dir)

    out_path = os.path.join(
        out_dir,
        f"{heat_pump_type}_{performance_level}_{weather_year}_{future_year}.csv",
    )

    # --- 3. Build half-hourly COP profiles for each grid square ---
    grid_id_list = air_temp_daily.columns
    list_of_cops = []

    # Half-hourly index for the future year (using n_days from air_temp_daily)
    full_index = pd.date_range(
        start=f"{future_year}-01-01",
        periods=n_days * 48,
        freq="30min",
    )

    for grid_id in grid_id_list:
        data = []

        for day in range(n_days):
            date = datetime(future_year, 1, 1) + timedelta(days=day)
            temp = air_temp_daily[grid_id].iloc[day]

            cop = average_day_cop_for_heat_pump(
                heat_pump_type,
                performance_level,
                temp,
            )

            # Repeat the daily COP value 48 times for 48 half-hours
            data.extend([cop] * 48)

        df = pd.DataFrame({grid_id: data}, index=full_index)
        list_of_cops.append(df)

    df_cops = pd.concat(list_of_cops, axis=1)

    # --- 4. Save to file ---
    df_cops.to_csv(out_path)

    return df_cops

if __name__ == '__main__':
    df = day_cop_for_year_grid_sq('ASHP', 'very good', future_year=2050, weather_year=2012)
    print(df)
