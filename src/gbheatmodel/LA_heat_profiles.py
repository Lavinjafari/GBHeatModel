from __future__ import annotations

from pathlib import Path
from glob import glob
import os

import numpy as np
import pandas as pd
import geopandas as gpd


def read_hd_profiles_from_folder(folder: str | Path) -> dict[str, pd.DataFrame]:
    """
    Read GBHeat half-hourly grid-level heat profiles.

    Each CSV is expected to contain half-hourly heat demand by technology.
    Units are kWh per half-hour.
    """

    folder = Path(folder)
    files = glob(str(folder / "*.csv"))

    profiles = {}

    for file in files:
        name = os.path.basename(file)

        grid_id = (
            name.replace("half_hourly_heat_profile_", "")
                .replace(".csv", "")
        )

        parts = grid_id.split("_")
        grid_id = "_".join(parts[0:2])

        df = pd.read_csv(file, index_col=0)
        df.index = pd.to_datetime(df.index)

        profiles[grid_id] = df

    return profiles


def build_grid_annual_heat_map(
    profiles: dict[str, pd.DataFrame],
    grid_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Convert grid-level half-hourly profiles to annual heat demand
    and merge with the Atlite grid geometry.
    """

    grid_hd = pd.DataFrame({
        "Grid_ID": list(profiles.keys()),
        "Annual_Heat_GWh": [
            df.sum(axis=1).sum() / 1e6
            for df in profiles.values()
        ],
    })

    grid_gdf = grid_gdf.copy()

    if "Grid_ID" not in grid_gdf.columns:
        grid_gdf["Grid_ID"] = (
            grid_gdf["x"].astype(str)
            + "_"
            + grid_gdf["y"].astype(str)
        )

    grid_map = grid_gdf.merge(
        grid_hd,
        on="Grid_ID",
        how="left",
    )

    return grid_map


def prepare_fes_stock_index(
    fes_matched: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Prepare LA-level FES heating stock index.

    Expects FES data already matched to 2021 LA boundaries.
    """

    fes = fes_matched.copy()

    if "LAD21NM" not in fes.columns:
        fes = fes.reset_index().rename(columns={"index": "LAD21NM"})

    fes = fes.rename(columns={"CODE_x": "LAD21CD"})

    meta_cols = ["LAD21CD", "LAD21NM", "Year", "Scenario", "Sector"]

    tech_cols = [
        c for c in fes.columns
        if c not in meta_cols + ["Total", "TotalHPs"]
        and pd.api.types.is_numeric_dtype(fes[c])
    ]

    fes[tech_cols] = fes[tech_cols].fillna(0)
    fes["FES_Total_Heat_Stock"] = fes[tech_cols].sum(axis=1)

    fes_stock_index = fes[
        ["LAD21CD", "LAD21NM", "FES_Total_Heat_Stock"] + tech_cols
    ].copy()

    return fes_stock_index, tech_cols


def redistribute_grid_heat_to_las(
    grid_map: gpd.GeoDataFrame,
    la_gdf: gpd.GeoDataFrame,
    fes_stock_index: pd.DataFrame,
    method: str = "fes_stock",
) -> tuple[gpd.GeoDataFrame, pd.DataFrame, gpd.GeoDataFrame]:
    """
    Redistribute grid-level annual heat demand to Local Authorities.

    Parameters
    ----------
    grid_map:
        Atlite grid GeoDataFrame with Grid_ID and Annual_Heat_GWh.

    la_gdf:
        Local Authority boundary GeoDataFrame with LAD21CD and LAD21NM.

    fes_stock_index:
        LA-level FES stock table with LAD21CD, LAD21NM and FES_Total_Heat_Stock.

    method:
        "fes_stock" or "fes_stock_area".

    Returns
    -------
    overlay_la:
        Grid-LA intersection table with redistribution factors.

    la_demand:
        LA-level annual heat demand table.

    la_map:
        LA GeoDataFrame for mapping.
    """

    grid_for_overlay = (
        grid_map
        .dropna(subset=["Annual_Heat_GWh"])
        .to_crs(epsg=27700)
        .copy()
    )

    la_for_overlay = la_gdf.to_crs(epsg=27700).copy()

    overlay_la = gpd.overlay(
        grid_for_overlay[["Grid_ID", "Annual_Heat_GWh", "geometry"]],
        la_for_overlay[["LAD21CD", "LAD21NM", "geometry"]],
        how="intersection",
    )

    overlay_la["intersection_area_m2"] = overlay_la.geometry.area

    overlay_la = overlay_la.merge(
        fes_stock_index,
        on=["LAD21CD", "LAD21NM"],
        how="left",
    )

    overlay_la["FES_Total_Heat_Stock"] = (
        overlay_la["FES_Total_Heat_Stock"]
        .fillna(0)
    )

    if method == "fes_stock":

        overlay_la["Redistribution_Weight"] = overlay_la["FES_Total_Heat_Stock"]

    elif method == "fes_stock_area":

        la_area = la_for_overlay[["LAD21CD", "geometry"]].copy()
        la_area["LA_total_area_m2"] = la_area.geometry.area

        overlay_la = overlay_la.merge(
            la_area[["LAD21CD", "LA_total_area_m2"]],
            on="LAD21CD",
            how="left",
        )

        overlay_la["Redistribution_Weight"] = (
            overlay_la["FES_Total_Heat_Stock"]
            * overlay_la["intersection_area_m2"]
            / overlay_la["LA_total_area_m2"]
        )

    else:
        raise ValueError(
            "method must be either 'fes_stock' or 'fes_stock_area'"
        )

    overlay_la["grid_total_weight"] = (
        overlay_la
        .groupby("Grid_ID")["Redistribution_Weight"]
        .transform("sum")
    )

    overlay_la["Stock_Redistribution_Factor"] = np.where(
        overlay_la["grid_total_weight"] > 0,
        overlay_la["Redistribution_Weight"] / overlay_la["grid_total_weight"],
        0,
    )

    overlay_la["Allocated_Heat_GWh"] = (
        overlay_la["Annual_Heat_GWh"]
        * overlay_la["Stock_Redistribution_Factor"]
    )

    la_demand = (
        overlay_la
        .groupby(["LAD21CD", "LAD21NM"], as_index=False)["Allocated_Heat_GWh"]
        .sum()
    )

    la_map = la_for_overlay.merge(
        la_demand,
        on=["LAD21CD", "LAD21NM"],
        how="left",
    )

    return overlay_la, la_demand, la_map


def build_la_half_hourly_profiles_by_technology(
    profiles: dict[str, pd.DataFrame],
    overlay_la: gpd.GeoDataFrame,
) -> dict[str, pd.DataFrame]:
    """
    Generate LA-level half-hourly heat profiles by technology.

    Returns
    -------
    dict
        key = LAD21CD
        value = DataFrame indexed by datetime, columns = heat technologies.
        Units are kWh per half-hour.
    """

    weights = overlay_la[
        ["Grid_ID", "LAD21CD", "LAD21NM", "Stock_Redistribution_Factor"]
    ].copy()

    weights = weights[weights["Stock_Redistribution_Factor"] > 0].copy()

    la_profiles = {}

    for grid_id, grid_profile in profiles.items():

        grid_weights = weights[weights["Grid_ID"] == grid_id]

        if grid_weights.empty:
            continue

        tech_cols = grid_profile.columns

        for _, row in grid_weights.iterrows():

            la_code = row["LAD21CD"]
            la_name = row["LAD21NM"]
            factor = row["Stock_Redistribution_Factor"]

            allocated = grid_profile[tech_cols] * factor

            if la_code not in la_profiles:
                la_profiles[la_code] = allocated.copy()
                la_profiles[la_code]["LAD21NM"] = la_name
            else:
                la_profiles[la_code][tech_cols] = (
                    la_profiles[la_code][tech_cols]
                    .add(allocated, fill_value=0)
                )

    return la_profiles


def save_la_profiles(
    la_profiles: dict[str, pd.DataFrame],
    output_dir: str | Path,
    FES_year: str,
    scenario: str,
    future_year: int,
) -> Path:
    """
    Save one half-hourly technology profile CSV per LA.
    """

    output_dir = Path(output_dir)

    profile_dir = (
        output_dir
        / f"LA_half_hourly_profiles_{FES_year}_{scenario}_{future_year}"
    )

    profile_dir.mkdir(parents=True, exist_ok=True)

    for la_code, df in la_profiles.items():

        la_name = df["LAD21NM"].iloc[0]

        out = df.drop(columns=["LAD21NM"]).copy()
        out.index.name = "datetime"

        safe_name = (
            la_name.replace("/", "-")
            .replace("\\", "-")
            .replace(" ", "_")
        )

        out_path = profile_dir / f"{safe_name}_heat_profile.csv"
        out.to_csv(out_path)

    return profile_dir