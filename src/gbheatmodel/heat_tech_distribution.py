from __future__ import annotations

import geopandas as gpd
import pandas as pd

# internal package imports
from .  import FES_heat_supply_data
from .  import FES_shapefile_LAs_matching
from .path import path_in_data, ensure_dir


def merge_shapefile_FES_heating_tech_file(
    grid_squares: gpd.GeoDataFrame,
    LA_overlaps: pd.DataFrame,
    future_year: int,
    FES_year: str,
    scenario: str,
    weather_year: int,
) -> pd.DataFrame:
    """
    Merge LA–grid overlap information with FES heating technology data.

    Parameters
    ----------
    grid_squares : GeoDataFrame
        Grid square geometries (not directly used here but kept for symmetry).
    LA_overlaps : DataFrame
        Output of LA_overlaps_within_grid_squares.calc_LA_overlap_within_grid_square.
    future_year : int
        Target future year (e.g. 2050).
    FES : str
        FES dataset identifier (e.g. "2022").
    scenario : str
        Scenario name (e.g. "LW", "CT", "ST", "FS").
    weather_year : int
        Weather year (kept for interface consistency).

    Returns
    -------
    DataFrame
        DataFrame indexed by Grid_ID with LA information and FES tech columns.
    """

    # FES heat supply per LA
    df_FES = FES_heat_supply_data.year_FES_heat_supply(
        future_year,
        FES_year,
        scenario,
    )

    # Harmonise FES LA naming with shapefile-based LA definitions
    df = FES_shapefile_LAs_matching.match_FES_and_shapefile_LAs(
        df_FES,
        future_year,
        FES_year,
        scenario,
    )

    # (Optional) tech list if needed somewhere else
    _list_of_tech = df.columns.values[4:18]

    # Clean / align LA naming
    LA_overlaps["Local_Authority"] = LA_overlaps["Local_Authority"].astype(str)
    df.index = df.index.astype(str)

    LA_overlaps = LA_overlaps[
        LA_overlaps["Local_Authority"].notna()
        & (LA_overlaps["Local_Authority"] != "None")
    ]

    LA_overlaps["Local_Authority"] = (
        LA_overlaps["Local_Authority"].str.strip().str.title()
    )
    df.index = df.index.str.strip().str.title()

    print("Sample FES LAs:", df.index.tolist()[:10])
    print("Sample Grid LAs:", LA_overlaps["Local_Authority"].unique()[:10])

    # Merge overlaps with FES data (many grid cells per LA)
    df_merged = pd.merge(
        LA_overlaps,
        df,
        left_on="Local_Authority",
        right_index=True,
        how="left",
        validate="m:1",
    )

    # Build Grid_ID as "x_y"
    df_merged["Grid_ID"] = df_merged.apply(
        lambda row: f"{row['grid_x']}_{row['grid_y']}",
        axis=1,
    )
    df_merged.set_index("Grid_ID", inplace=True)

    # Save merged result
    out_path = path_in_data(
        "Outputs",
        "merged_FES_heat_tech.csv",
    )
    ensure_dir(out_path.parent)
    df_merged.to_csv(out_path, index=False)

    return df_merged


def distribute_all_heating_techs_to_grids(
    df_merged: pd.DataFrame,
) -> pd.DataFrame:
    """
    Distribute LA-level FES heating technologies to grid squares
    according to LA–grid overlap percentages.

    Parameters
    ----------
    df_merged : DataFrame
        Output of merge_shapefile_FES_heating_tech_file, containing:
        - 'Grid_ID', 'Local_Authority', 'Year', 'Scenario', 'Sector',
        - 'overlap_percentage',
        - technology columns (from column index 13 onward).

    Returns
    -------
    DataFrame
        DataFrame with heating techs distributed to each grid square.
    """

    # Assume technology columns start from column index 13 onward
    list_of_tech = df_merged.columns[13:]
    distributed_heat_tech: list[pd.DataFrame] = []

    for LA in df_merged["Local_Authority"].unique():
        df_LA = df_merged[df_merged["Local_Authority"] == LA].copy()
        perc_sum = df_LA["overlap_percentage"].sum()

        if perc_sum == 0:
            continue

        df_LA = df_LA.reset_index()

        # Normalise overlap_percentage once per LA
        df_LA["normalized_overlap"] = (
            df_LA["overlap_percentage"] / df_LA["overlap_percentage"].sum()
        )

        for tech in list_of_tech:
            tech_total = df_LA[tech].iloc[0]
            df_LA[tech] = df_LA["normalized_overlap"] * tech_total

        keep_cols = [
            "Grid_ID",
            "Local_Authority",
            "Year",
            "Scenario",
            "Sector",
            *list_of_tech,
        ]
        distributed_heat_tech.append(df_LA[keep_cols])

    df_out = pd.concat(distributed_heat_tech, ignore_index=True)

    out_path = path_in_data(
        "Outputs",
        "distributed_heat_tech.csv",
    )
    ensure_dir(out_path.parent)
    df_out.to_csv(out_path, index=False)

    return df_out


if __name__ == "__main__":
    weather_year = 2010
    FES = "2022"
    future_year = 2050
    scenario = "LW"

    # Load shapefile and grid-squares for the test run
    LA_path = path_in_data(
        "LAs_shapefile_2021",
        "LAD_DEC_2021_GB_BFC.shp",
    )
    grids_path = path_in_data(
        "UK_Atlite_Grid_sq.gpkg",
    )

    LA_shapefile = gpd.read_file(LA_path)
    grid_squares = gpd.read_file(grids_path)

    from . import LA_overlaps_within_grid_squares  # imported here to avoid circulars

    LA_overlaps = LA_overlaps_within_grid_squares.calc_LA_overlap_within_grid_square(
        grid_squares,
        LA_shapefile,
        weather_year,
    )

    # Merge shapefile with FES heating technology data
    df_merged = merge_shapefile_FES_heating_tech_file(
        grid_squares,
        LA_overlaps,
        future_year,
        FES,
        scenario,
        weather_year,
    )

    # Distribute heating technologies to grid squares
    distributed_heat_tech_df = distribute_all_heating_techs_to_grids(df_merged)

    print(distributed_heat_tech_df.head())
