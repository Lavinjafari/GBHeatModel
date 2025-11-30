from __future__ import annotations

import pandas as pd
import pprint

# internal package imports
from . import heat_pattern_heat_demand as hphd
from .path import path_in_data, ensure_dir


def heat_demand_per_pattern_per_grid_sq_one_day(
    grid_id: str,
    Td: float,
    weather_year: int,
) -> dict[str, float]:
    """
    Calculate daily heat demand per heating pattern for a single grid square,
    for one day with average temperature Td.

    Parameters
    ----------
    grid_id : str
        Grid square ID (not directly used in the formula yet, but kept
        for consistency and possible extensions).
    Td : float
        Average daily external temperature [°C].
    weather_year : int
        Weather year (kept for interface consistency).

    Returns
    -------
    dict[str, float]
        Dictionary:
            {
                "daytime":    HD_daytime,
                "bi-modal":   HD_bimodal,
                "continuous": HD_continuous,
            }
    """

    HD_pattern = {
        "daytime": hphd.heat_demand_for_one_pattern_for_one_day("daytime", Td),
        "bi-modal": hphd.heat_demand_for_one_pattern_for_one_day("bi-modal", Td),
        "continuous": hphd.heat_demand_for_one_pattern_for_one_day("continuous", Td),
    }

    return HD_pattern


if __name__ == "__main__":
    # Example manual test for one grid square across the whole year
    grid_id = "-0.25_50.75"
    weather_year = 2012

    # Paths for air temperature
    avg_air_temp_path = path_in_data(
        "air_temp",
        f"average_day_air_temp_{weather_year}.csv",
    )
    air_temp_daily = pd.read_csv(avg_air_temp_path, index_col=0)

    # Ensure output directory
    out_dir = path_in_data("outputs",)
    ensure_dir(out_dir)

    # We will collect results for all days in a single DataFrame
    records = []

    for day in range(365):
        Td = air_temp_daily[grid_id].iloc[day]
        HD_dict = heat_demand_per_pattern_per_grid_sq_one_day(grid_id, Td, weather_year)

        date = pd.Timestamp(f"{weather_year}-01-01") + pd.Timedelta(days=day)
        record = {"date": date, **HD_dict}
        records.append(record)

        print(f"\n📅 Day {day + 1} ({date.date()}), Td = {Td:.2f}°C")
        pprint.pprint(HD_dict)

    df = pd.DataFrame(records).set_index("date")

    out_path = out_dir / f"heat_demand_one_day_patterns_{grid_id}_{weather_year}.csv"
    df.to_csv(out_path)

    print("\n✅ Saved CSV:", out_path)
    print("✅ Saved CSV shape:", df.shape)
