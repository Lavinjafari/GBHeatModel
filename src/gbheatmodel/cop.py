import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from calendar import isleap

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
    # Read air temperature data
    air_temp_daily = pd.read_csv(f'data/LA_UK/new_version/air_temp_new/average_day_air_temp_{weather_year}.csv', index_col=0)

    # Convert to datetime index for safety
    air_temp_daily.index = pd.date_range(start=f"{weather_year}-01-01", periods=len(air_temp_daily), freq='D')

    # Drop Feb 29 if future year is NOT leap
    if not isleap(future_year):
        air_temp_daily = air_temp_daily[~((air_temp_daily.index.month == 2) & (air_temp_daily.index.day == 29))]

    grid_id_list = air_temp_daily.columns
    list_of_cops = []

    # Define the correct datetime index for half-hourly steps
    full_index = pd.date_range(start=f"{future_year}-01-01", periods=365 * 48, freq="30min")

    for grid_id in grid_id_list:
        data = []

        for day in range(365):  # Non-leap year
            date = datetime(future_year, 1, 1) + timedelta(days=day)
            temp = air_temp_daily[grid_id].iloc[day]
            cop = average_day_cop_for_heat_pump(heat_pump_type, performance_level, temp)

            # Repeat the daily COP value 48 times for 48 half-hours
            data.extend([cop] * 48)

        df = pd.DataFrame({grid_id: data}, index=full_index)
        list_of_cops.append(df)

    df_cops = pd.concat(list_of_cops, axis=1)

    # Save to file
    output_dir = 'data/LA_UK/new_version/outputs/COP_Profiles'
    os.makedirs(output_dir, exist_ok=True)
    file_name = f"{heat_pump_type}_{performance_level}_{weather_year}_{future_year}.csv"
    file_path = os.path.join(output_dir, file_name)
    df_cops.to_csv(file_path)

    return df_cops

# def day_cop_for_year_grid_sq(heat_pump_type, performance_level, future_year, weather_year):

#     # try to read file first
#     # try:
#     #     df_cops = pd.read_csv('data/cop_profiles/' + heat_pump_type + '_' + performance_level + '_' + str(weather_year) + '_' + str(future_year) + '.csv', index_col=0)
#     # except:
#     # read in daily temps
#     air_temp_daily = pd.read_csv('data/LA_UK/new_version/air_temp_new/average_day_air_temp_' + str(weather_year) + '.csv', index_col=0)

#     grid_id_list = air_temp_daily.columns
#     # print(LA_list)

#     list_of_cops = []
#     for grid_id in grid_id_list:
#         # calculate the average COP over a day
#         daysinyear = 365 #+ calendar.isleap(future_year)
#         data = {}
#         for day in range(1, daysinyear):
#             date_time = str(day) + '-' + str(future_year)
#             data[date_time] = average_day_cop_for_heat_pump(heat_pump_type, performance_level, air_temp_daily[grid_id].iloc[day])
#         df = pd.DataFrame(data, index=[grid_id]).T
#         time_added = str(1) + '-' + str(future_year + 1)
#         df.loc[time_added] = 0
#         # random non-leap year used. but year is modified later.
#         start = str(2021) + '-01-01'
#         end = str(2021) + '-12-31 23:30:00'
#         datetime_index = pd.date_range(start=start, end=end, freq='D')
#         df.index = datetime_index
#         # df.index = pd.to_datetime(df.index, format="%j-%Y")
#         df = df.resample('0.5h').ffill()
#         df = df[:-1]
#         df.index = df.index.map(lambda dt: dt.replace(year=future_year))
#         # df.index = df.index + pd.DateOffset(year=future_year)

#         list_of_cops.append(df)
    
#     df_cops = pd.concat(list_of_cops, axis=1)
#     output_dir = 'data/LA_UK/new_version/outputs/COP_Profiles'
#     os.makedirs(output_dir, exist_ok=True)

#     file_name = f"{heat_pump_type}_{performance_level}_{weather_year}_{future_year}.csv"
#     file_path = os.path.join(output_dir, file_name)

#     df_cops.to_csv(file_path)

#     return df_cops

if __name__ == '__main__':
    df = day_cop_for_year_grid_sq('ASHP', 'very good', future_year=2050, weather_year=2012)
    print(df)
