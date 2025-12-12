import pandas as pd
import numpy as np
import os
from gbheatmodel.path import path_in_data, ensure_dir


def electric_demand_for_heat(HD_profiles, grid_sqs, df_ASHP, df_GSHP):
    """
    Convert heat-demand profiles to electric-demand profiles using COP profiles.

    Parameters
    ----------
    HD_profiles : dict[str, pd.DataFrame]
        Mapping grid_id -> heat demand DataFrame (DatetimeIndex).
    grid_sqs : list[str]
        Grid IDs to process.
    df_ASHP : pd.DataFrame
        ASHP COP profiles. Index=time, columns=grid_id.
    df_GSHP : pd.DataFrame
        GSHP COP profiles. Index=time, columns=grid_id.

    Returns
    -------
    dict[str, pd.DataFrame]
        Mapping grid_id -> electric demand DataFrame (DatetimeIndex).
    """

    # Ensure COP indices are datetime once
    df_ASHP = df_ASHP.copy()
    df_GSHP = df_GSHP.copy()
    df_ASHP.index = pd.to_datetime(df_ASHP.index)
    df_GSHP.index = pd.to_datetime(df_GSHP.index)

    ed_grid_sqs = {}

    required_cols = [
        "ASHP",
        "GSHP",
        "Hybrid (ASHP + BioLPG boiler)",
        "Hybrid (ASHP + Hydrogen boiler)",
        "Hybrid (ASHP + Electric resistive)",
    ]

    for grid_id in grid_sqs:
        if grid_id not in HD_profiles:
            print(f"⚠️ Skipping {grid_id}: not found in heat demand data.")
            continue
        if grid_id not in df_ASHP.columns or grid_id not in df_GSHP.columns:
            print(f"⚠️ Skipping {grid_id}: not found in COP data.")
            continue

        # Heat demand for this grid
        elec_hd_df = HD_profiles[grid_id].loc[:, required_cols].copy()
        elec_hd_df.index = pd.to_datetime(elec_hd_df.index)

        # COP series for this grid aligned to heat-demand index
        cop_ASHP = df_ASHP[grid_id].reindex(elec_hd_df.index)
        cop_GSHP = df_GSHP[grid_id].reindex(elec_hd_df.index)

        # Electricity demand
        elec_hd_df["ASHP Elec"] = elec_hd_df["ASHP"] / cop_ASHP
        elec_hd_df["GSHP Elec"] = elec_hd_df["GSHP"] / cop_GSHP

        elec_hd_df["Hybrid (ASHP + BioLPG boiler) Elec"] = (
            0.70 * elec_hd_df["Hybrid (ASHP + BioLPG boiler)"] / cop_ASHP
        )
        elec_hd_df["Hybrid (ASHP + Hydrogen boiler) Elec"] = (
            0.90 * elec_hd_df["Hybrid (ASHP + Hydrogen boiler)"] / cop_ASHP
        )
        elec_hd_df["Hybrid (ASHP + Electric resistive) Elec"] = (
            0.90 * elec_hd_df["Hybrid (ASHP + Electric resistive)"] / cop_ASHP
            + 0.10 * elec_hd_df["Hybrid (ASHP + Electric resistive)"]
        )

        ed_grid_sqs[grid_id] = elec_hd_df[
            [
                "ASHP Elec",
                "GSHP Elec",
                "Hybrid (ASHP + BioLPG boiler) Elec",
                "Hybrid (ASHP + Hydrogen boiler) Elec",
                "Hybrid (ASHP + Electric resistive) Elec",
            ]
        ]

    return ed_grid_sqs
