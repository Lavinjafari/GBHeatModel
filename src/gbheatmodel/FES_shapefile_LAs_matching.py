# src/gbheatmodel/FES_shapefile_LAs_matching.py

from __future__ import annotations

from typing import Optional, Iterable

import geopandas as gpd
import pandas as pd

# internal package imports
from . import FES_heat_supply_data
from .path import path_in_data, ensure_dir


def find_mismatch_FES_shapefile(
    LAs_FES: Optional[pd.DataFrame] = None,
    LA_shapefile: Optional[gpd.GeoDataFrame] = None,
) -> pd.DataFrame:
    """
    Compare LA names between the FES locations file and the LA shapefile,
    and report matches and mismatches.

    Parameters
    ----------
    LAs_FES : DataFrame, optional
        Pre-loaded FES LA locations. If None, will be read from
        data/LA_UK/new_version/uk_LA_locations_FES.csv.
    LA_shapefile : GeoDataFrame, optional
        Pre-loaded LA shapefile. If None, will be read from
        data/LA_UK/new_version/UK_LAs_Boundaries_files/LAs_shapefile_2021/...

    Returns
    -------
    DataFrame
        Comparison table with matching and mismatching LAs and their coordinates.
    """

    # Load shapefile and FES locations if not provided
    if LA_shapefile is None:
        LA_path = path_in_data(
            "LAs_shapefile_2021",
            "LAD_DEC_2021_GB_BFC.shp",
        )
        LA_shapefile = gpd.read_file(LA_path)

    if LAs_FES is None:
        fes_path = path_in_data("uk_LA_locations_FES.csv")
        LAs_FES = pd.read_csv(fes_path, index_col=0)

    shapefile_LAs = LA_shapefile[["LAD21NM", "LONG", "LAT", "LAD21CD"]].drop_duplicates()
    shapefile_LAs.columns = ["name", "LONG", "LAT", "LAD21CD"]
    shapefile_LAs["name"] = shapefile_LAs["name"].str.lower()

    LAs_FES = LAs_FES.copy()
    LAs_FES["name"] = LAs_FES["name"].str.lower()

    # Matching / mismatching LAs
    matching_LAs = set(shapefile_LAs["name"]).intersection(set(LAs_FES["name"]))
    only_in_shapefile_LAs = set(shapefile_LAs["name"]) - set(LAs_FES["name"])
    only_in_LAs_FES = set(LAs_FES["name"]) - set(shapefile_LAs["name"])

    # Pad lists to same length
    max_length = max(
        len(matching_LAs),
        len(only_in_shapefile_LAs),
        len(only_in_LAs_FES),
    )
    matching_padded = list(matching_LAs) + [None] * (max_length - len(matching_LAs))
    shapefile_padded = list(only_in_shapefile_LAs) + [None] * (
        max_length - len(only_in_shapefile_LAs)
    )
    fes_padded = list(only_in_LAs_FES) + [None] * (max_length - len(only_in_LAs_FES))

    list_of_LAs = pd.DataFrame(
        {
            "matching_LAs": matching_padded,
            "only_in_shapefile_LAs": shapefile_padded,
            "only_in_LAs_FES": fes_padded,
        }
    )

    # Map coordinates for matching / mismatched LAs
    LAs_FES.set_index("name", inplace=True)
    list_of_LAs["matching_long"] = list_of_LAs["matching_LAs"].map(LAs_FES["x"])
    list_of_LAs["matching_lat"] = list_of_LAs["matching_LAs"].map(LAs_FES["y"])

    list_of_LAs["fes_long"] = list_of_LAs["only_in_LAs_FES"].map(LAs_FES["x"])
    list_of_LAs["fes_lat"] = list_of_LAs["only_in_LAs_FES"].map(LAs_FES["y"])

    shapefile_LAs.set_index("name", inplace=True)
    list_of_LAs["shapefile_long"] = list_of_LAs["only_in_shapefile_LAs"].map(
        shapefile_LAs["LONG"]
    )
    list_of_LAs["shapefile_lat"] = list_of_LAs["only_in_shapefile_LAs"].map(
        shapefile_LAs["LAT"]
    )
    list_of_LAs["CODE_x"] = list_of_LAs["only_in_shapefile_LAs"].map(
        shapefile_LAs["LAD21CD"]
    )

    # Reorder columns
    list_of_LAs = list_of_LAs[
        [
            "matching_LAs",
            "matching_long",
            "matching_lat",
            "only_in_shapefile_LAs",
            "shapefile_long",
            "shapefile_lat",
            "CODE_x",
            "only_in_LAs_FES",
            "fes_long",
            "fes_lat",
        ]
    ]

    # Optional: save comparison to CSV
    # out_path = path_in_data("LA_UK", "new_version", "list_of_LAs_comparison.csv")
    # ensure_dir(out_path.parent)
    # list_of_LAs.to_csv(out_path, index=False)

    return list_of_LAs


def match_FES_and_shapefile_LAs(
    df: Optional[pd.DataFrame],
    future_year: int,
    FES: str,
    scenario: str,
) -> pd.DataFrame:
    """
    Match and aggregate FES heat-supply data to updated LA definitions.

    Parameters
    ----------
    df : DataFrame or None
        Existing FES heat-supply DataFrame. If None, it is loaded internally
        using year_FES_heat_supply(future_year, FES, scenario).
    future_year : int
        Target future year (e.g. 2050).
    FES : str
        FES dataset version (e.g. "2022").
    scenario : str
        Scenario code ("LW", "CT", "ST", "FS", ...).

    Returns
    -------
    DataFrame
        Aggregated and code-updated LA-level FES data.
    """

    # If no DataFrame passed in, load FES heat supply data.
    if df is None:
        df = FES_heat_supply_data.year_FES_heat_supply(future_year, FES, scenario)

    df = df.copy()
    df.columns = df.columns.str.replace(r"stock ", "", regex=False)
    df.index = df.index.str.replace("Chiltern District", "Chiltern")
    df.index = df.index.str.replace("South Bucks District", "South Bucks")
    df.index = df.index.str.replace("Wycombe District", "Wycombe")
    df.index = df.index.str.replace("Aylesbury Vale District", "Aylesbury Vale")

    aggregation = {
        "North Northamptonshire": [
            "East Northamptonshire",
            "Corby",
            "Wellingborough",
            "Kettering",
        ],
        "West Northamptonshire": [
            "Daventry",
            "Northampton",
            "South Northamptonshire",
        ],
        "Buckinghamshire": ["South Bucks", "Chiltern", "Aylesbury Vale", "Wycombe"],
    }

    non_sum = ["CODE_x", "Year", "Scenario", "Sector"]
    aggregated_rows = []

    for new_LA, org_LA in aggregation.items():
        try:
            group_df = df.loc[org_LA]
        except KeyError as e:
            print(f"Missing LAs in original data: {e}")
            continue

        base_info = group_df.iloc[0][non_sum].copy()
        base_info["index"] = new_LA

        numeric_sum = (
            group_df.drop(columns=non_sum, errors="ignore")
            .apply(pd.to_numeric, errors="coerce")
            .sum()
        )
        full_row = pd.concat([base_info, numeric_sum])
        aggregated_rows.append(full_row)

    aggregated_df = pd.DataFrame(aggregated_rows)
    aggregated_df.set_index("index", inplace=True)

    # Drop originals and append aggregated rows
    all_originals = [la for group in aggregation.values() for la in group]
    df = df.drop(index=all_originals, errors="ignore")
    df = pd.concat([df, aggregated_df], axis=0)

    new_codes = {
        "North Northamptonshire": "E06000061",
        "West Northamptonshire": "E06000062",
        "Buckinghamshire": "E06000060",
    }

    new_LAs_mask = df.index.isin(new_codes.keys())
    df.loc[new_LAs_mask, "CODE_x"] = df.loc[new_LAs_mask].index.map(new_codes)

    df.index = df.index.map(str)
    df = df.sort_index()
    df.rename(columns={"index": "Local_Authority"}, inplace=True)

    # Optional: save matched FES output
    # out_path = path_in_data("LA_UK", "new_version", "matched_FES_heating.csv")
    # ensure_dir(out_path.parent)
    # df.to_csv(out_path, index=False)

    return df


if __name__ == "__main__":
    # Example usage / basic test
    LA_path = path_in_data(
        "LAs_shapefile_2021",
        "LAD_DEC_2021_GB_BFC.shp",
    )
    fes_path = path_in_data("uk_LA_locations_FES.csv")
    
    LA_shapefile = gpd.read_file(LA_path)
    LAs_FES = pd.read_csv(fes_path, index_col=0)

    list_of_LAs = find_mismatch_FES_shapefile(LAs_FES, LA_shapefile)
    print(list_of_LAs.head())

    weather_year = 2024
    FES = "2022"
    future_year = 2050
    scenario = "LW"

    df_raw = FES_heat_supply_data.year_FES_heat_supply(future_year, FES, scenario)
    matched_FES = match_FES_and_shapefile_LAs(df_raw, future_year, FES, scenario)
    print(matched_FES.head())
