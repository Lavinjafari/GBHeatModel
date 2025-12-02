
import geopandas as gpd
import pandas as pd

# centralised paths from the package
from .path import path_in_data, ensure_dir


def calc_LA_overlap_within_grid_square(
    grid_squares: gpd.GeoDataFrame,
    LA_shapefile: gpd.GeoDataFrame,
    weather_year: int,
) -> pd.DataFrame:
    """
    Calculate how much each Local Authority (LA) overlaps with each grid square.

    Parameters
    ----------
    grid_squares : GeoDataFrame
        Grid squares with 'x' and 'y' columns and geometry.
    LA_shapefile : GeoDataFrame
        Local Authority polygons with LAD21NM / LAD21CD and LONG / LAT.
    weather_year : int
        Weather year (kept for interface consistency; not used internally yet).

    Returns
    -------
    DataFrame
        DataFrame indexed by Grid_ID with overlap percentage and LA info.
    """

    # Ensure both layers are in the same CRS
    if grid_squares.crs != LA_shapefile.crs:
        grid_squares = grid_squares.to_crs(LA_shapefile.crs)

    # Geometrical intersection between grid squares and LAs
    LAs_overlaps = gpd.overlay(grid_squares, LA_shapefile, how="intersection")

    # Calculate overlap areas and relative overlap within each LA
    LAs_overlaps["overlap_area"] = LAs_overlaps.geometry.area
    LAs_overlaps["LA_area"] = (
        LAs_overlaps.groupby("LAD21NM")["overlap_area"].transform("sum")
    )
    LAs_overlaps["overlap_percentage"] = (
        LAs_overlaps["overlap_area"] / LAs_overlaps["LA_area"] * 100.0
    )

    # Build a grid_id from x and y
    LAs_overlaps["grid_id"] = LAs_overlaps.apply(
        lambda row: f"{row['x']}_{row['y']}", axis=1
    )

    # Clean / rename columns
    for col in ["LAD21NMW", "BNG_E", "BNG_N", "GlobalID", "geometry"]:
        if col in LAs_overlaps.columns:
            LAs_overlaps.drop(columns=[col], inplace=True)

    LAs_overlaps.rename(
        columns={
            "LAD21NM": "Local_Authority",
            "LAD21CD": "LA_Code",
            "x": "grid_x",
            "y": "grid_y",
            "LONG": "long",
            "LAT": "lat",
            "grid_id": "Grid_ID",
        },
        inplace=True,
    )

    LAs_overlaps.set_index("Grid_ID", inplace=True)

    # Save to a consistent location inside this project
    # out_path = path_in_data(
    #     "Outputs",
    #     "perc_LAs_in_grid_square.csv",
    # )
    # ensure_dir(out_path.parent)
    # LAs_overlaps.to_csv(out_path)

    return LAs_overlaps


if __name__ == "__main__":
    weather_year = 2024
    FES = "2022"        # unused here but kept for consistency with other scripts
    future_year = 2050  # unused here
    scenario = "LW"     # unused here

    # Load shapefile and grid squares using centralised paths
    LA_path = path_in_data(
        "LAs_shapefile_2021",
        "LAD_DEC_2021_GB_BFC.shp",
    )
    grids_path = path_in_data(
        "UK_Atlite_Grid_sq.gpkg",
    )

    LA_shapefile = gpd.read_file(LA_path)
    grid_squares = gpd.read_file(grids_path)

    # Calculate overlaps and percentages
    LAs_overlaps = calc_LA_overlap_within_grid_square(
        grid_squares,
        LA_shapefile,
        weather_year,
    )

    print(LAs_overlaps.head())
