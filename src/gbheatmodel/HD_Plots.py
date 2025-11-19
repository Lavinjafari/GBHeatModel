import pandas as pd
import matplotlib.pyplot as plt
from glob import glob
import os
import seaborn as sns



def plot_daily_avg_profile_one_grid(scaled_profiles_dict, grid_id):
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
    plt.show()



def plot_heatmap_one_grid(scaled_profiles_dict, grid_id):
    if grid_id not in scaled_profiles_dict:
        print(f"Grid ID '{grid_id}' not found.")
        return

    df = scaled_profiles_dict[grid_id]

    for tech in df.columns:
        daily_matrix = df[tech].values.reshape(-1, 48)
        plt.figure(figsize=(12, 5))
        sns.heatmap(daily_matrix, cmap='YlGnBu', cbar_kws={'label': 'kWh'})
        plt.title(f"Heatmap of {tech} Demand – Grid {grid_id}")
        plt.xlabel("Half-Hour of Day")
        plt.ylabel("Day of Year")
        plt.tight_layout()
        plt.show()


def plot_total_daily_demand(scaled_profiles_dict, grid_id=None):
    """
    Plots total daily heat demand (summed across all technologies),
    either for all grid squares combined or for a specific grid square.

    Parameters:
    -----------
    scaled_profiles_dict : dict
        Dictionary mapping grid_id to DataFrame of half-hourly profiles.
    grid_id : str, optional
        If provided, plots daily demand for this specific grid square only.
    """
    if grid_id:
        if grid_id not in scaled_profiles_dict:
            print(f"Grid ID '{grid_id}' not found.")
            return
        combined_df = scaled_profiles_dict[grid_id]
        title_prefix = f"Grid {grid_id}"
    else:
        combined_df = sum((df for df in scaled_profiles_dict.values()))
        title_prefix = "All Grid Squares"

    total_demand = combined_df.sum(axis=1)  # sum across all techs
    daily_total = total_demand.values.reshape(-1, 48).sum(axis=1)  # sum across 48 slots per day

    plt.figure(figsize=(12, 4))
    plt.plot(range(1, 366), daily_total)
    plt.xlabel("Day of Year")
    plt.ylabel("Total Heat Demand (kWh)")
    plt.title(f"Total Daily Heat Demand – {title_prefix}")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_week_of_heat_profiles(folder_path, start_date="2050-07-04", days=7, num_grids=3):
    """
    Plots a week of half-hourly heat demand profiles for a selection of grid squares.

    Parameters:
    -----------
    folder_path : str
        Path to the folder containing scaled profile CSVs.
    start_date : str
        Start date for the time window to plot (format: YYYY-MM-DD).
    days : int
        Number of days to plot from start_date.
    num_grids : int
        Number of grid profiles to load and plot.
    """
    from datetime import datetime, timedelta

    # Generate date range
    start = pd.to_datetime(start_date)
    end = start + pd.Timedelta(days=days)

    # Get CSVs
    csv_files = glob(os.path.join(folder_path, "*.csv"))

    if not csv_files:
        print("No CSV files found in the specified folder.")
        return

    # Load and plot
    example_profiles = {}
    for file in csv_files[:num_grids]:
        basename_parts = os.path.basename(file).split("_")
        grid_id = "_".join(basename_parts[4:-3])  # handles cases like '-0.5_52.0'
        df = pd.read_csv(file, index_col=0, parse_dates=True)
        example_profiles[grid_id] = df

    # Plot each grid
    for grid_id, df in example_profiles.items():
        sample = df.loc[start:end]
        sample.plot(figsize=(14, 6), title=f"Half-Hourly Heat Demand – Grid {grid_id} ({start.date()} to {end.date()})")
        plt.ylabel("Heat Demand (kWh)")
        plt.xlabel("Date-Time")
        plt.grid(True)
        plt.tight_layout()
        plt.show()
        
def plot_boxplot_half_hourly_distribution(scaled_profiles_dict, grid_ids=None):
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
        


def plot_selected_grids_daily_demand(scaled_profiles_dict, grid_ids):
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
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
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
