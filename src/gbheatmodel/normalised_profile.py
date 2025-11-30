from __future__ import annotations

import pandas as pd

from .path import path_in_data


def half_hourly_normalised_profiles(
    heat_pattern_data: pd.DataFrame,
    Td: float,
) -> pd.Series:
    """
    Select the appropriate half-hourly normalised profile column
    based on the daily average temperature Td.

    Parameters
    ----------
    heat_pattern_data : DataFrame
        DataFrame with 8 columns, each column corresponding to a
        temperature band of the normalised half-hourly profile.
    Td : float
        Average daily external temperature [°C].

    Returns
    -------
    Series
        Selected half-hourly normalised profile (length 48).
    """
    normalised_profile = heat_pattern_data

    if Td < -4.5:
        normalised_profile = normalised_profile.iloc[:, 0]
        # raise ValueError(f"Only day temperatures above -4.5 degrees are accepted: {Td}")
    elif -4.5 <= Td < -1.5:
        normalised_profile = normalised_profile.iloc[:, 0]
    elif -1.5 <= Td < 1.5:
        normalised_profile = normalised_profile.iloc[:, 1]
    elif 1.5 <= Td < 4.5:
        normalised_profile = normalised_profile.iloc[:, 2]
    elif 4.5 <= Td < 7.5:
        normalised_profile = normalised_profile.iloc[:, 3]
    elif 7.5 <= Td < 10.5:
        normalised_profile = normalised_profile.iloc[:, 4]
    elif 10.5 <= Td < 13.5:
        normalised_profile = normalised_profile.iloc[:, 5]
    elif 13.5 <= Td < 16.5:
        normalised_profile = normalised_profile.iloc[:, 6]
    elif Td >= 16.5:
        normalised_profile = normalised_profile.iloc[:, 7]

    return normalised_profile


if __name__ == "__main__":
    # Example manual test using the package data path helper
    profiles_path = path_in_data("normalised_half_hourly_profiles.xlsx")

    normalised_profiles = {
        "daytime": pd.read_excel(
            profiles_path,
            sheet_name="Total heat daytime HPs",
            usecols="B:I",
        ),
        "bi-modal": pd.read_excel(
            profiles_path,
            sheet_name="Total heat bimodal HPs",
            usecols="B:I",
        ),
        "continuous": pd.read_excel(
            profiles_path,
            sheet_name="Total heat continuous HPs",
            usecols="B:I",
        ),
    }

    heat_pattern_data = normalised_profiles["daytime"]
    Td = 10.0

    normalised_profile = half_hourly_normalised_profiles(heat_pattern_data, Td)
    print(normalised_profile)
    print(f"T_d = {Td:.1f} → pattern sum = {normalised_profile.sum():.6f}")
