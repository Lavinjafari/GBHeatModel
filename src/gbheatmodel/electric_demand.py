import pandas as pd
import numpy as np
import os
from gbheatmodel.path import path_in_data, ensure_dir


def electric_demand_for_heat(
        HD_profiles,
        grid_sqs,
        df_ASHP,
        df_GSHP,
        *,
        biofuel_hybrid_ashp_share=None,
    ):
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
        "Hybrid (ASHP + Hydrogen boiler)",
        "Hybrid (ASHP + Electric resistive)",
    ]

    biolpg_hybrid = "Hybrid (ASHP + BioLPG boiler)"
    biofuel_hybrid = "Hybrid (ASHP + Biofuel boiler)"

    if biofuel_hybrid_ashp_share is not None:
        if not 0 <= biofuel_hybrid_ashp_share <= 1:
            raise ValueError(
                "biofuel_hybrid_ashp_share must be between 0 and 1."
            )

    for grid_id in grid_sqs:
        if grid_id not in HD_profiles:
            print(f"⚠️ Skipping {grid_id}: not found in heat demand data.")
            continue
        if grid_id not in df_ASHP.columns or grid_id not in df_GSHP.columns:
            print(f"⚠️ Skipping {grid_id}: not found in COP data.")
            continue

        # Heat demand for this grid
        heat_df = HD_profiles[grid_id]

        has_biolpg = biolpg_hybrid in heat_df.columns
        has_biofuel = biofuel_hybrid in heat_df.columns

        if has_biolpg == has_biofuel:
            raise ValueError(
                f"Grid {grid_id}: expected exactly one of "
                "BioLPG or Biofuel hybrid technologies."
            )

        hybrid_tech = biolpg_hybrid if has_biolpg else biofuel_hybrid

        if has_biofuel and biofuel_hybrid_ashp_share is None:
            raise ValueError(
                "FES Biofuel hybrid detected. Specify its ASHP heat "
                "share explicitly before calculating electricity demand."
            )

        missing = [col for col in required_cols if col not in heat_df.columns]

        if missing:
            raise ValueError(
                f"Grid {grid_id}: missing heat-demand columns: {missing}"
            )

        elec_hd_df = heat_df.loc[:, required_cols + [hybrid_tech]].copy()
        elec_hd_df.index = pd.to_datetime(elec_hd_df.index)

        # COP series for this grid aligned to heat-demand index
        cop_ASHP = df_ASHP[grid_id].reindex(elec_hd_df.index)
        cop_GSHP = df_GSHP[grid_id].reindex(elec_hd_df.index)

        # Electricity demand
        elec_hd_df["ASHP Elec"] = elec_hd_df["ASHP"] / cop_ASHP
        elec_hd_df["GSHP Elec"] = elec_hd_df["GSHP"] / cop_GSHP

        hybrid_ashp_share = (
            0.70
            if has_biolpg
            else biofuel_hybrid_ashp_share
        )

        hybrid_elec_col = f"{hybrid_tech} Elec"

        elec_hd_df[hybrid_elec_col] = (
            hybrid_ashp_share * elec_hd_df[hybrid_tech] / cop_ASHP
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
                hybrid_elec_col,
                "Hybrid (ASHP + Hydrogen boiler) Elec",
                "Hybrid (ASHP + Electric resistive) Elec",
            ]
        ]

    return ed_grid_sqs
