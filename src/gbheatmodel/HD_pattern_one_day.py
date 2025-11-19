import pandas as pd
import numpy as np
from collections import defaultdict

import heat_pattern_heat_demand as hphd
import pprint



def heat_demand_per_pattern_per_grid_sq_one_day(grid_id,Td,weather_year):
    
    
    
    # total_dwellings = base_pattern  # Total number of dwellings (1 dwelling)

    # daytime = total_dwellings['daytime']
    # bimodal = total_dwellings['bi-modal']
    # continuous = total_dwellings['continuous']
    HD_pattern = {'daytime': hphd.heat_demand_for_one_pattern_for_one_day('daytime', Td) ,
               'bi-modal': hphd. heat_demand_for_one_pattern_for_one_day('bi-modal', Td) ,
               'continuous': hphd.heat_demand_for_one_pattern_for_one_day('continuous', Td)}
    
    df = pd.DataFrame({k: [v] for k, v in HD_pattern.items()})

    return HD_pattern




if __name__ == "__main__":
    # Inputs
    grid_id = "-0.25_50.75"
    weather_year = 2012
    air_temp_daily = pd.read_csv('data/LA_UK/new_version/air_temp_new/average_day_air_temp_' + str(weather_year) + '.csv')
    grid_sqs = pd.read_csv('data/LA_UK/new_version/air_temp_new/air_temp_2012.csv', index_col=0).columns

    for day in range(0, 365):
        Td = air_temp_daily[grid_id].iloc[day]

        # Run and return the dictionary
        HD_dict = heat_demand_per_pattern_per_grid_sq_one_day(grid_id, Td)

        # 🔍 Pretty print the dictionary
        print(f"\n📅 Day {day + 1}")
        pprint.pprint(HD_dict)

        # Convert to DataFrame for saving
        df = pd.DataFrame({k: [v] for k, v in HD_dict.items()})
        df.to_csv(f'data/LA_UK/new_version/test/heat_demand_one_day_patterns_{grid_id}.csv')

        print("✅ Saved CSV shape:", df.shape)

    