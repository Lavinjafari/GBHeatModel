import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from calendar import isleap
from .path import path_in_data, ensure_dir

def average_day_cop_for_heat_pump(heat_pump_type, performance_level, Td):
    """
    Calculate average COP over a day for a heat pump given:
    - heat_pump_type: 'ASHP' or 'GSHP'
    - performance_level: 'current', 'good', 'very good', ...
    - Td: average day temperature [°C]
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


def day_cop_for_year_grid_sq(
    heat_pump_type: str,
    performance_level: str,
    future_year: int,
    weather_year: int,
    air_temp_daily: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build half-hourly COP time series for each grid square for one year.

    Parameters
    ----------
    heat_pump_type
        'ASHP' or 'GSHP'.
    performance_level
        e.g. 'current', 'good', 'very good'.
    future_year
        Target future year for time index.
    weather_year
        Weather year from which daily temps come (for documentation only).
    air_temp_daily
        DataFrame with daily average air temperatures per grid:
        index: daily datetime for weather_year (or any year, length = n_days),
        columns: grid IDs.

    Returns
    -------
    DataFrame
        Half-hourly COP profiles:
        index: DatetimeIndex for future_year (n_days * 48 steps),
        columns: grid IDs.
    """
    air_temp_daily = air_temp_daily.copy()
    air_temp_daily.index = pd.to_datetime(air_temp_daily.index)

    # Drop Feb 29 if needed
    if not isleap(future_year):
        air_temp_daily = air_temp_daily[
            ~((air_temp_daily.index.month == 2) & (air_temp_daily.index.day == 29))
        ]

    n_days = len(air_temp_daily)
    full_index = pd.date_range(
        start=f"{future_year}-01-01",
        periods=n_days * 48,
        freq="30min",
    )

    grid_id_list = air_temp_daily.columns
    list_of_cops = []

    for grid_id in grid_id_list:
        data = []
        for day in range(n_days):
            temp = air_temp_daily[grid_id].iloc[day]
            cop_val = average_day_cop_for_heat_pump(heat_pump_type, performance_level, temp)
            data.extend([cop_val] * 48)

        df = pd.DataFrame({grid_id: data}, index=full_index)
        list_of_cops.append(df)

    df_cops = pd.concat(list_of_cops, axis=1)
    return df_cops

if __name__ == '__main__':
    df = day_cop_for_year_grid_sq('ASHP', 'very good', future_year=2050, weather_year=2012)
    print(df)
