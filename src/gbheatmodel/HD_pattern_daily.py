from __future__ import annotations

import pandas as pd

# internal package imports
from . import HD_pattern_one_day as hd_one_day
from . import heat_pattern_heat_demand as hphd  # kept for future use if needed
from .path import path_in_data


def heat_demand_per_pattern_per_grid_sq_daily(
    grid_id: str,
    air_temp_daily: pd.DataFrame,
    weather_year: int,
) -> pd.DataFrame:
    """
    Compute daily heat demand per heating pattern for a given grid square
    over an entire year.

    Parameters
    ----------
    grid_id : str
        Grid square ID string, e.g. "-0.25_50.75".
    air_temp_daily : DataFrame
        Daily average air temperature for all grid squares.
        Columns: grid IDs, index: day-of-year or dates.
    weather_year : int
        Weather year (e.g. 2012).

    Returns
    -------
    DataFrame
        Index: date (DatetimeIndex), columns: ['daytime', 'bi-modal', 'continuous'].
        Values: daily heat demand per pattern for that grid.
    """

    # Extract air temperature series for this grid square
    air_temp_series = air_temp_daily[grid_id]
    daysinyear = 365

    # Dictionary to collect results
    results = {}

    for day in range(daysinyear):
        date_str = (pd.Timestamp(f"{weather_year}-01-01") + pd.Timedelta(days=day)).strftime("%Y-%m-%d")
        Td = air_temp_series.iloc[day]

        # Get pattern-wise daily demand for this grid square and temperature
        pattern_values = hd_one_day.heat_demand_per_pattern_per_grid_sq_one_day(grid_id, Td, weather_year)
        
        # pattern_values should be a dictionary like {'daytime': x, 'bi-modal': y, 'continuous': z}
        results[date_str] = pattern_values

    # Convert to DataFrame: rows = date, columns = pattern
    df = pd.DataFrame.from_dict(results, orient='index')

    # Make sure columns are ordered
    df = df[['daytime', 'bi-modal', 'continuous']]

    # Convert index to datetime
    df.index = pd.to_datetime(df.index)
    df.index.name = 'date'

    return df

if __name__ == "__main__":
    weather_year = 2012

    # Paths for air temperature files
    avg_air_temp_path = path_in_data(
        "air_temp",
        f"average_day_air_temp_{weather_year}.csv",
    )
    air_temp_grid_path = path_in_data(
        "air_temp",
        f"air_temp_{weather_year}.csv",
    )

    # Load daily average temperatures
    air_temp_daily = pd.read_csv(avg_air_temp_path, index_col=0)
    grid_sqs = pd.read_csv(air_temp_grid_path, index_col=0).columns

    # Example grid square
    grid_id = "-0.25_50.75"

    df = heat_demand_per_pattern_per_grid_sq_daily(grid_id, air_temp_daily, weather_year)
    print(df.head())
