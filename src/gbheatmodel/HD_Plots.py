import pandas as pd
import matplotlib.pyplot as plt
from glob import glob
import os
import seaborn as sns

from gbheatmodel.path import path_in_data  


def _save_current_figure(
    filename: str,
    subfolder: str,
    dpi: int = 300,
) -> None:
    """
    Save the current Matplotlib figure into outputs/plots/<subfolder>/filename.
    """
    plots_dir = path_in_data("outputs", "plots", subfolder)
    os.makedirs(plots_dir, exist_ok=True)

    filepath = os.path.join(plots_dir, filename)
    fig = plt.gcf()
    fig.savefig(filepath, dpi=dpi, bbox_inches="tight")
    print(f"💾 Plot saved to: {filepath}")


def plot_daily_avg_profile_one_grid(
    scaled_profiles_dict,
    grid_id,
    *,
    save: bool = False,
    subfolder: str = "daily_avg_profiles",
    filename: str | None = None,
):    
    
    if grid_id not in scaled_profiles_dict:
        print(f"Grid ID '{grid_id}' not found.")
        return
    
    df = scaled_profiles_dict[grid_id]
    daily_avg_profiles = {}
    
    for tech in df.columns:
        tech_series = df[tech]
        daily_matrix = tech_series.values.reshape(-1, 48)
        daily_avg = daily_matrix.mean(axis=0)
        daily_avg_profiles[tech] = daily_avg

    plt.figure(figsize=(12, 6))
    time_axis = [f"{int(i/2):02d}:{'30' if i%2 else '00'}" for i in range(48)]

    for tech, profile in daily_avg_profiles.items():
        plt.plot(time_axis, profile, label=tech)

        plt.title(f"Daily Average Heating Profile – Grid {grid_id}")
    plt.xlabel("Time of Day")
    plt.ylabel("Average Demand (kWh)")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    if save:
        if filename is None:
            filename = f"daily_avg_grid_{grid_id}.png"
        _save_current_figure(filename, subfolder=subfolder)

    plt.show()

def plot_heatmap_one_grid(
    scaled_profiles_dict,
    grid_id,
    *,
    save: bool = False,
    subfolder: str = "grid_heatmaps",
):
    """
    Plot a heatmap of half-hourly heat demand for one grid,
    one heatmap per technology.

    Rows  = days of year
    Cols  = 48 half-hour slots per day
    Cells = demand (kWh)
    """

    if grid_id not in scaled_profiles_dict:
        print(f"Grid ID '{grid_id}' not found.")
        return

    df = scaled_profiles_dict[grid_id]

    if df.empty:
        print(f"No data for grid {grid_id}.")
        return

    for tech in df.columns:
        series = df[tech]
        n = len(series)

        if n % 48 != 0:
            print(
                f"Tech '{tech}' in grid {grid_id} has length {n}, "
                "not divisible by 48 – skipping."
            )
            continue

        # reshape to [days, 48 half-hour slots]
        daily_matrix = series.values.reshape(-1, 48)

        plt.figure(figsize=(10, 6))
        sns.heatmap(
            daily_matrix,
            cmap="YlOrRd",
            cbar_kws={"label": "Heat Demand (kWh)"},
        )
        plt.title(f"Heatmap of {tech} Demand – Grid {grid_id}")
        plt.xlabel("Half-Hour of Day (0–47)")
        plt.ylabel("Day of Year (0–N)")
        plt.tight_layout()

        if save:
            filename = f"heatmap_{tech}_grid_{grid_id}.png"
            _save_current_figure(filename, subfolder=subfolder)

        plt.show()



def plot_total_daily_demand(
    profiles,
    grid_id=None,
    *,
    save: bool = False,
    subfolder: str = "total_daily_demand",
    filename: str | None = None,
):
    """
    Plots total daily heat demand (summed across all technologies),
    either for all grid squares combined or for a specific grid square.

    Parameters
    ----------
    profiles : dict
        Dictionary mapping grid_id to DataFrame of half-hourly profiles.
    grid_id : str, optional
        If provided, plots daily demand for this specific grid square only.
        If None, aggregates all grids (national total).
    """

    # 1. Choose which DataFrame(s) to aggregate
    if grid_id is not None:
        if grid_id not in profiles:
            print(f"Grid ID '{grid_id}' not found.")
            return
        combined_df = profiles[grid_id]
        title_prefix = f"Grid {grid_id}"
    else:
        # Sum all grids; assumes all DataFrames share same index/columns
        combined_df = sum(df for df in profiles.values())
        title_prefix = "All Grid Squares"

    # If nothing there, bail out
    if combined_df.empty:
        print("Combined DataFrame is empty, nothing to plot.")
        return

    # 2. Sum over technologies -> half-hourly total
    total_demand = combined_df.sum(axis=1)  # Series, length N

    n = len(total_demand)
    if n == 0:
        print("Total demand series is empty, nothing to plot.")
        return

    if n % 48 != 0:
        print(f"Length {n} is not divisible by 48; "
              "cannot reshape into full days. Nothing plotted.")
        return

    # 3. Aggregate to daily totals (sum over 48 half-hours)
    daily_total = total_demand.values.reshape(-1, 48).sum(axis=1)

    # 4. Build a day index
    if isinstance(total_demand.index, pd.DatetimeIndex):
        day_index = pd.date_range(
            start=total_demand.index[0].normalize(),
            periods=len(daily_total),
            freq="D",
        )
    else:
        day_index = range(len(daily_total))

    # 5. Plot
    plt.figure(figsize=(12, 5))
    plt.plot(day_index, daily_total)
    plt.title(f"Total Daily Heat Demand – {title_prefix}")
    plt.xlabel("Date" if isinstance(day_index, pd.DatetimeIndex) else "Day")
    plt.ylabel("Total Heat Demand (kWh)")
    plt.grid(True)
    plt.tight_layout()

    # 6. Optional save
    if save:
        if filename is None:
            if grid_id is not None:
                filename = f"total_daily_grid_{grid_id}.png"
            else:
                filename = "total_daily_all_grids.png"
        _save_current_figure(filename, subfolder=subfolder)

    plt.show()



def plot_week_of_heat_profiles(
    profiles_dict,
    grid_id,
    *,
    start_date="2050-01-15",
    days=7,
    save=False,
    subfolder="weekly_profiles",
    filename_grid=None,
    filename_all=None,
):
    """
    Plot a week of half-hourly heat demand:

      1) For a specific grid_id
      2) For ALL grids combined (national)

    Parameters
    ----------
    profiles_dict : dict
        {grid_id -> DataFrame of half-hourly profiles (index: datetime, cols: techs)}
    grid_id : str
        Grid ID to plot individually.
    start_date : str
        Start date (YYYY-MM-DD).
    days : int
        Number of days to plot from start_date.
    """

    # --- basic checks ---
    if grid_id not in profiles_dict:
        print(f"Grid ID '{grid_id}' not found in profiles_dict.")
        return

    start = pd.to_datetime(start_date)
    end   = start + pd.Timedelta(days=days)

    # ========= 1) SPECIFIC GRID =========
    df_grid = profiles_dict[grid_id]

    if not isinstance(df_grid.index, pd.DatetimeIndex):
        print(f"Grid {grid_id} does not have a DatetimeIndex. Cannot slice by date.")
    else:
        week_grid = df_grid.loc[start:end]

        if week_grid.empty:
            print(f"No data for grid {grid_id} between {start} and {end}.")
        else:
            # sum over technologies
            series_grid = week_grid.sum(axis=1)

            plt.figure(figsize=(14, 5))
            plt.plot(series_grid.index, series_grid.values)
            plt.title(f"Half-Hourly Heat Demand – Grid {grid_id}\n({start.date()} to {end.date()})")
            plt.xlabel("Date-Time")
            plt.ylabel("Heat Demand (kWh)")
            plt.grid(True)
            plt.tight_layout()

            if save:
                if filename_grid is None:
                    filename_grid = f"week_grid_{grid_id}_{start.date()}_{end.date()}.png"
                _save_current_figure(filename_grid, subfolder=subfolder)

            plt.show()

    # ========= 2) ALL GRIDS (NATIONAL) =========
    # sum all grids → combined_df: same index, tech columns
    combined_df = sum(df for df in profiles_dict.values())

    if not isinstance(combined_df.index, pd.DatetimeIndex):
        print("Combined DataFrame index is not DatetimeIndex. Cannot slice by date.")
        return

    week_all = combined_df.loc[start:end]

    if week_all.empty:
        print(f"No data for ALL grids between {start} and {end}.")
        return

    series_all = week_all.sum(axis=1)  # sum over techs

    plt.figure(figsize=(14, 5))
    plt.plot(series_all.index, series_all.values)
    plt.title(f"Half-Hourly Heat Demand – ALL Grids\n({start.date()} to {end.date()})")
    plt.xlabel("Date-Time")
    plt.ylabel("Heat Demand (kWh)")
    plt.grid(True)
    plt.tight_layout()

    if save:
        if filename_all is None:
            filename_all = f"week_all_grids_{start.date()}_{end.date()}.png"
        _save_current_figure(filename_all, subfolder=subfolder)

    plt.show()


        
def plot_boxplot_half_hourly_distribution(
    scaled_profiles_dict,
    grid_ids=None,
    *,
    save: bool = False,
    subfolder: str = "half_hourly_boxplots",
    filename: str | None = None,
):

    """
    Plots a boxplot showing distribution of half-hourly demand across all days
    for either selected grid IDs or all grids.

    Parameters:
    -----------
    scaled_profiles_dict : dict
        Dictionary mapping grid_id to DataFrame of half-hourly profiles.
    grid_ids : list of str, optional
        Specific grid IDs to include. If None, uses all grids.
    """
    if grid_ids is None:
        selected_dict = scaled_profiles_dict
        title_prefix = "All Grids"
    else:
        grid_ids = [gid for gid in grid_ids if gid in scaled_profiles_dict]
        if not grid_ids:
            print("❌ No valid grid IDs provided.")
            return
        selected_dict = {gid: scaled_profiles_dict[gid] for gid in grid_ids}
        title_prefix = ", ".join(grid_ids)

    # Sum across all techs per grid and across grids
    combined_df = sum(df.sum(axis=1) for df in selected_dict.values())
    daily_matrix = combined_df.values.reshape(-1, 48)  # 365 x 48

    # Plot boxplot
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=pd.DataFrame(daily_matrix))
    plt.xlabel("Half-Hour Interval (0–47)")
    plt.ylabel("Total Heat Demand (kWh)")
    plt.title(f"Half-Hourly Demand Distribution — {title_prefix}")
    plt.tight_layout()
    plt.grid(True)

    if save:
        if filename is None:
            filename = f"boxplot_{title_prefix.replace(' ', '_')}.png"
        _save_current_figure(filename, subfolder=subfolder)

    plt.show()
       

def plot_boxplot_half_hourly_distribution(scaled_profiles_dict, grid_ids=None):
    """
    Plots a boxplot showing distribution of half-hourly demand across all days
    for either selected grid IDs or all grids.
    """
    if grid_ids is None:
        selected_dict = scaled_profiles_dict
        title_prefix = "All Grids"
    else:
        grid_ids = [gid for gid in grid_ids if gid in scaled_profiles_dict]
        if not grid_ids:
            print("❌ No valid grid IDs provided.")
            return
        selected_dict = {gid: scaled_profiles_dict[gid] for gid in grid_ids}
        title_prefix = ", ".join(grid_ids)

    # Sum across all techs per grid and across grids
    combined_df = sum(df.sum(axis=1) for df in selected_dict.values())
    daily_matrix = combined_df.values.reshape(-1, 48)  # 365 x 48

    # Plot boxplot
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=pd.DataFrame(daily_matrix))
    plt.xlabel("Half-Hour Interval (0–47)")
    plt.ylabel("Total Heat Demand (kWh)")
    plt.title(f"Half-Hourly Demand Distribution — {title_prefix}")
    plt.tight_layout()
    plt.grid(True)
    plt.show()
        


def plot_selected_grids_daily_demand(
    scaled_profiles_dict,
    grid_ids=None,
    *,
    save: bool = False,
    subfolder: str = "half_hourly_boxplots",
    filename: str | None = None,
):
    """
    Plots total daily heat demand for specified grid IDs.

    Parameters:
    -----------
    scaled_profiles_dict : dict
        Dictionary mapping grid_id to DataFrame of half-hourly heat demand per tech.
    grid_ids : list of str
        List of specific grid IDs to plot.
    """
    # Validate input grid IDs
    missing = [gid for gid in grid_ids if gid not in scaled_profiles_dict]
    if missing:
        print(f"⚠️ These grid IDs were not found: {missing}")

    grid_ids = [gid for gid in grid_ids if gid in scaled_profiles_dict]
    if not grid_ids:
        print("❌ No valid grid IDs to plot.")
        return

    # Compute total daily demand for each grid
    grid_df = pd.DataFrame({
        gid: scaled_profiles_dict[gid].sum(axis=1).values.reshape(-1, 48).sum(axis=1)
        for gid in grid_ids
    })

    day_index = pd.date_range(start="2050-01-01", periods=365, freq="D")

    # Plot
    plt.figure(figsize=(14, 6))
    for gid in grid_df.columns:
        plt.plot(day_index, grid_df[gid], label=f"Grid {gid}")

    plt.xlabel("Date")
    plt.ylabel("Total Daily Heat Demand (kWh)")
    plt.title(f"Daily Heat Demand for Selected Grids: {', '.join(grid_df.columns)}")
    plt.tight_layout()
    plt.grid(True)

    if save:
        if filename is None:
            filename = f"boxplot_{title_prefix.replace(' ', '_')}.png"
        _save_current_figure(filename, subfolder=subfolder)

    plt.show()

    return grid_df  # Return the daily demand data for reuse



def plot_tech_heatmaps(scaled_profiles_dict):
    combined_df = sum((df for df in scaled_profiles_dict.values()))
    for tech in combined_df.columns:
        tech_series = combined_df[tech]
        tech_matrix = tech_series.values.reshape(-1, 48)
        plt.figure(figsize=(12, 5))
        sns.heatmap(tech_matrix, cmap="YlOrRd", cbar_kws={'label': 'Heat Demand (kWh)'})
        plt.title(f"Heatmap of {tech} Demand (Days x Half-Hour Slots)")
        plt.xlabel("Half-Hour of Day")
        plt.ylabel("Day of Year")
        plt.tight_layout()
        plt.show()

def plot_area_full_year(profiles, grid_id=None):
    """
    Publication-style stacked area plot of half-hourly heat demand
    across the full year.

    If grid_id=None:
        Sum all grid cells and plot national heat demand.

    Otherwise:
        Plot the selected grid cell only.
    """

    # ========================================================
    # 0. Reset any previously applied matplotlib style
    # ========================================================

    plt.style.use("default")


    # ========================================================
    # 1. Select national or grid-level profile
    # ========================================================

    if grid_id is None:

        df = sum(
            profile for profile in profiles.values()
        )

        title = "Annual Half-Hourly Heat Demand"

    else:

        df = profiles[grid_id]

        title = (
            f"Annual Half-Hourly Heat Demand – Grid {grid_id}"
        )


    if df.empty:
        print("DataFrame is empty, cannot plot.")
        return


    # ========================================================
    # 2. Create figure
    # ========================================================

    fig, ax = plt.subplots(
        figsize=(18, 7),
        facecolor="white"
    )

    ax.set_facecolor("white")


    # ========================================================
    # 3. Stacked area plot
    # ========================================================

    df.plot.area(
        ax=ax,
        stacked=True,
        cmap="tab20",
        linewidth=0
    )


    # ========================================================
    # 4. Title and axis labels
    # ========================================================

    ax.set_title(
        title,
        fontsize=24,
        fontweight="bold",
        pad=20
    )

    ax.set_xlabel(
        "Date",
        fontsize=18,
        fontweight="bold",
        labelpad=10
    )

    ax.set_ylabel(
        "Heat Demand (kWh per half-hour)",
        fontsize=18,
        fontweight="bold",
        labelpad=10
    )


    # ========================================================
    # 5. Tick labels
    # ========================================================

    ax.tick_params(
        axis="both",
        which="major",
        labelsize=15
    )


    # ========================================================
    # 6. Grid
    # ========================================================

    # Horizontal grid only
    ax.grid(
        axis="y",
        alpha=0.25,
        linewidth=0.8
    )

    ax.grid(
        axis="x",
        visible=False
    )


    # ========================================================
    # 7. Clean frame
    # ========================================================

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


    # ========================================================
    # 8. Legend
    # ========================================================

    ax.legend(
        title="Heating Technology",
        fontsize=12,
        title_fontsize=13,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=4
    )


    # ========================================================
    # 9. Layout
    # ========================================================

    fig.subplots_adjust(
        bottom=0.23
    )

    plt.show()

def plot_area_one_week(
    profiles,
    grid_id=None,
    start_date="2050-01-01",
    days=7,
):
    """
    Stacked area plot of half-hourly heat demand for a selected week.
    If grid_id=None: plot national.
    """

    start = pd.to_datetime(start_date)
    end = start + pd.Timedelta(days=days)

    # --- Select grid or all grids ---
    if grid_id is None:
        df = sum(df for df in profiles.values())
        label = "National"
    else:
        df = profiles[grid_id]
        label = f"Grid {grid_id}"

    if not isinstance(df.index, pd.DatetimeIndex):
        print("Index must be DatetimeIndex to slice by week.")
        return

    week_df = df.loc[start:end]

    if week_df.empty:
        print("No data available for this week/time period.")
        return

    plt.style.use("ggplot")
    week_df.plot.area(figsize=(20, 8), cmap="tab20", stacked=True)
    plt.title(f"Weekly Heat Demand – {label}\n{start.date()} to {end.date()}")
    plt.xlabel("Date-Time")
    plt.ylabel("Heat Demand (kWh)")
    plt.tight_layout()
    plt.show()
