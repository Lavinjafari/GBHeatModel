import pandas as pd
from collections import defaultdict

import HD_pattern_one_day as hd_one_day
import heat_pattern_heat_demand as hphd


def heat_demand_per_pattern_per_grid_sq_daily(grid_id, air_temp_daily, weather_year):
    import pandas as pd

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

    air_temp_daily = pd.read_csv('data/LA_UK/new_version/air_temp_new/average_day_air_temp_' + str(weather_year) + '.csv')
    grid_sqs = pd.read_csv('data/LA_UK/new_version/air_temp_new/air_temp_2012.csv', index_col=0).columns

    grid_id = "-0.25_50.75"

    df = heat_demand_per_tech_per_grid_sq_daily(grid_id, air_temp_daily, weather_year)
    print(df.head())