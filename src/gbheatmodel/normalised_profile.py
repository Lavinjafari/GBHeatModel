import pandas as pd
import numpy as np


def half_hourly_normalised_profiles(heat_pattern_data, Td):

    normalised_profile = heat_pattern_data
    if Td < -4.5:
        normalised_profile = normalised_profile.iloc[:,0]
        # raise ValueError(f"Only day temperatures above -4.5 degrees are accepted: {Td}")
    elif Td >= -4.5 and Td < -1.5:
        normalised_profile = normalised_profile.iloc[:,0]
    elif Td >= -1.5 and Td < 1.5:
        normalised_profile = normalised_profile.iloc[:,1]
    elif Td >= 1.5 and Td < 4.5:
        normalised_profile = normalised_profile.iloc[:,2]
    elif Td >= 4.5 and Td < 7.5:
        normalised_profile = normalised_profile.iloc[:,3]
    elif Td >= 7.5 and Td < 10.5:
        normalised_profile = normalised_profile.iloc[:,4]
    elif Td >= 10.5 and Td < 13.5:
        normalised_profile = normalised_profile.iloc[:,5]
    elif Td >= 13.5 and Td < 16.5:
        normalised_profile = normalised_profile.iloc[:,6]
    elif Td >= 16.5:
        normalised_profile = normalised_profile.iloc[:,7]
    
    return normalised_profile


if __name__ == "__main__":
    normalised_profiles = {'daytime': pd.read_excel('data/normalised_half_hourly_profiles.xlsx', sheet_name='Total heat daytime HPs', usecols="B:I"),
                           'bi-modal': pd.read_excel('data/normalised_half_hourly_profiles.xlsx', sheet_name='Total heat bimodal HPs', usecols="B:I"),
                           'continuous': pd.read_excel('data/normalised_half_hourly_profiles.xlsx', sheet_name='Total heat continuous HPs', usecols="B:I")}
    heat_pattern_data = normalised_profiles['daytime']
    Td = 10
    normalised_profile = half_hourly_normalised_profiles(heat_pattern_data, Td)
    print(normalised_profile)
    print(f"T_d = {Td:.1f} → pattern sum = {normalised_profile.sum():.6f}")
