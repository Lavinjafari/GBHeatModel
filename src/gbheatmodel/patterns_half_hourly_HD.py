import pandas as pd
from collections import defaultdict
import HD_pattern_daily as hd_daily
import normalised_profile 
from datetime import datetime, timedelta

import os

def half_hourly_heat_demand_for_patterns_per_grid_sq(grid_id, air_temp_daily, weather_year, normalised_profiles):
    file_name = f"({grid_id})_{weather_year}.csv"
    folder = rf"data\LA_UK\new_version\outputs\heat_demand_profiles_patterns\HD_heat_patterns_{weather_year}"
    file_path = os.path.join(folder, file_name)

    if os.path.exists(file_path):
        df = pd.read_csv(file_path, index_col=0)
        df.index = pd.to_datetime(df.index)
        print(f"📂 Loaded existing file: {file_path}")
        return df

    print(f"📁 File not found. Generating: {file_path}")

    air_temp_series = air_temp_daily[grid_id]
    HD_daily = hd_daily.heat_demand_per_pattern_per_grid_sq_daily(grid_id, air_temp_daily, weather_year)

    # Ensure column names are stripped of whitespace
    HD_daily.columns = HD_daily.columns.str.strip().str.lower()

    profile_daytime_base = normalised_profiles['daytime']
    profile_bimodal_base = normalised_profiles['bi-modal']
    profile_continuous_base = normalised_profiles['continuous']

    df_list = []

    for day in range(365):  # Non-leap year
        day_date = datetime(weather_year, 1, 1) + timedelta(days=day)
        day_string = day_date.strftime("%Y-%m-%d")

        try:
            temp_day = air_temp_series.iloc[day]
            day_values = HD_daily.loc[day_string]

            # Check if patterns exist
            if not all(k in day_values.index for k in ['daytime', 'bi-modal', 'continuous']):
                print(f"⚠️ Missing patterns on {day_string}, skipping.")
                continue

            profile_daytime = normalised_profile.half_hourly_normalised_profiles(profile_daytime_base, temp_day)
            profile_bimodal = normalised_profile.half_hourly_normalised_profiles(profile_bimodal_base, temp_day)
            profile_continuous = normalised_profile.half_hourly_normalised_profiles(profile_continuous_base, temp_day)
            
            HD_pattern_half_hourly = {
                'daytime': day_values['daytime'] * profile_daytime,
                'bi-modal': day_values['bi-modal'] * profile_bimodal,
                'continuous': day_values['continuous'] * profile_continuous,
            }

            day_df = pd.DataFrame(HD_pattern_half_hourly)
            df_list.append(day_df)

        except Exception as e:
            print(f"❌ Error processing {day_string}: {e}")
            continue

    if not df_list:
        raise ValueError(f"❌ No valid daily data generated for grid_id={grid_id}!")

    df = pd.concat(df_list, axis=0)
    datetime_index = pd.date_range(start=datetime(weather_year, 1, 1), periods=len(df), freq='30min')
    df.index = datetime_index

    os.makedirs(folder, exist_ok=True)
    df.to_csv(file_path)
    print(f"💾 Saved new file: {file_path}")
    

    return df


def heat_demand_for_all_variables_grid_sq_half_hourly(grid_sqs, weather_year):

    air_temp_daily = pd.read_csv('data/LA_UK/new_version/air_temp_new/average_day_air_temp_' + str(weather_year) + '.csv')
    print(air_temp_daily.columns[:5]) 

    normalised_profiles = {'daytime': pd.read_excel('data/normalised_half_hourly_profiles.xlsx', sheet_name='Total heat daytime HPs', usecols="B:I"),
                           'bi-modal': pd.read_excel('data/normalised_half_hourly_profiles.xlsx', sheet_name='Total heat bimodal HPs', usecols="B:I"),
                           'continuous': pd.read_excel('data/normalised_half_hourly_profiles.xlsx', sheet_name='Total heat continuous HPs', usecols="B:I")}
    
    # get a list of LA
    # year dosent matter only used for getting LA list
    df = pd.read_csv('data/LA_UK/new_version/air_temp_new/air_temp_' + str(2015) + '.csv', index_col=0)
    grid_sqs = df.columns
    
    for grid_id in grid_sqs:
        print(grid_id, weather_year)
        half_hourly_heat_demand_for_patterns_per_grid_sq(grid_id, 
                                        air_temp_daily, 
                                        weather_year, 
                                        normalised_profiles
                                        )
        

if __name__ == "__main__":
    # Define the grid squares and weather year
    
    weather_year = 2010
    # weather_year_list = [2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
    # for weather_year in weather_year_list:
    #     print(f"Processing year: {weather_year}")
   
    grid_sqs = pd.read_csv('data/LA_UK/new_version/air_temp_new/air_temp_2012.csv', index_col=0).columns

    # Call the function to generate heat demand profiles
    heat_demand_for_all_variables_grid_sq_half_hourly(grid_sqs, weather_year)
 
