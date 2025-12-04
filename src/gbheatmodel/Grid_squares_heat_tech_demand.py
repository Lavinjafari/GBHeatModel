from __future__ import annotations

import geopandas as gpd
import pandas as pd

# internal package imports
from . import FES_heat_supply_data           # kept for future use if needed
from . import FES_shapefile_LAs_matching     # currently used indirectly via heat_tech_distribution
from . import LA_overlaps_within_grid_squares
from . import heat_tech_distribution
from .path import path_in_data, ensure_dir

def calculate_heat_demand_for_grid_squares(
    distributed_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate heating technology demand to grid-square  = total_dwellings.

    Parameters
    ----------
    total_dwellings : DataFrame
        Output of `distribute_all_heating_techs_to_grids`, containing:
        - 'Grid_ID'
        - possibly 'Local_Authority', 'Year', 'Scenario', 'Sector'
        - tech columns (numeric)

    Returns
    -------
    DataFrame
        Heat demand (or total_dwellings) per grid square and technology.
    """

    # Work on a copy to avoid modifying the caller's DataFrame
    df = distributed_df.copy()

    # Make sure Grid_ID is a column, not an index
    if "Grid_ID" in df.index.names:
        df = df.reset_index()

    # Identify non-tech metadata columns (keep flexible)
    meta_cols_base = ["Grid_ID", "Local_Authority", "Year", "Scenario", "Sector"]
    meta_cols = [col for col in meta_cols_base if col in df.columns]

    # Tech columns are numeric columns that are not in the metadata list
    tech_cols = df.select_dtypes(include="number").columns.difference(meta_cols)

    # 1. Aggregate numeric values per grid square
    total_dwellings = df.groupby("Grid_ID")[tech_cols].sum().reset_index()

    # 2. Get one row of metadata per Grid_ID (first occurrence)
    if any(c in df.columns for c in ["Year", "Scenario", "Sector"]):
        meta_cols_for_group = [c for c in ["Year", "Scenario", "Sector"] if c in df.columns]
        meta = (
            df.groupby("Grid_ID")[meta_cols_for_group]
            .first()
            .reset_index()
        )
        total_dwellings = pd.merge(
            total_dwellings,
            meta,
            on="Grid_ID",
            how="left",
        )

    # 3. Reorder columns: metadata first, then techs
    ordered_meta_cols = [c for c in ["Grid_ID", "Year", "Scenario", "Sector"] if c in total_dwellings.columns]
    ordered_tech_cols = [c for c in total_dwellings.columns if c not in ordered_meta_cols]
    total_dwellings = total_dwellings[ordered_meta_cols + ordered_tech_cols]

    # 4. Save to CSV (same behaviour as before)
    # out_path = path_in_data("outputs", "heat_techs_distribution_grid_square.csv")
    # ensure_dir(out_path.parent)
    # grid_square_hd.to_csv(out_path, index=False)

    return total_dwellings


def prepare_site_to_calc_air_temp(grid_square_hd: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare grid-square coordinate file for air-temperature calculation.

    Parameters
    ----------
    grid_square_hd : DataFrame
        Output from calculate_heat_demand_for_grid_squares, containing 'Grid_ID'.

    Returns
    -------
    DataFrame
        DataFrame with columns ['Grid_ID', 'x', 'y'] saved to CSV.
    """
    df = grid_square_hd[["Grid_ID"]].copy()

    # Separate x and y coordinates from 'Grid_ID'
    df[["x", "y"]] = df["Grid_ID"].str.split("_", expand=True).astype(float)

    # Save to CSV using centralised path
    out_path = path_in_data("outputs", "grid_square_coord.csv")
    ensure_dir(out_path.parent)
    df.to_csv(out_path, index=False)

    return df


if __name__ == "__main__":
    weather_year = 2024
    FES = "2022"
    future_year = 2050
    scenario = "LW"

    # Use path.py for shapefiles and grids
    LA_path = path_in_data(
        "LAs_shapefile_2021",
        "LAD_DEC_2021_GB_BFC.shp",
    )
    grids_path = path_in_data(
        "UK_Atlite_Grid_sq.gpkg",
    )

    LA_shapefile = gpd.read_file(LA_path)
    grid_squares = gpd.read_file(grids_path)

    LA_overlaps = LA_overlaps_within_grid_squares.calc_LA_overlap_within_grid_square(
        grid_squares, LA_shapefile, weather_year
    )

    # Calculate heat demand
    grid_square_hd = calculate_heat_demand_for_grid_squares(
        LA_overlaps,
        weather_year,
        future_year,
        FES,
        scenario,
        LA_shapefile,
        grid_squares,
    )

    # Use heat demand result to prepare air temperature grid
    site = prepare_site_to_calc_air_temp(grid_square_hd)
    print(site.head())
