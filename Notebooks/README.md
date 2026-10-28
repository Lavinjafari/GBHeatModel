# GBHeat — Notebooks

Practical examples for running and analysing **GBHeat**, the Great Britain residential heat-demand model. The notebooks use the existing `gbheatmodel` Python package under `src/`; they are **not independent implementations of the underlying scientific methods**.

> **Status:** These notebooks are being prepared for a public release. They have not all been tested together from a fresh environment with independently downloaded input data. In particular, verify the final plotting notebook against the reference paper figures before tagging a release.

## Notebook guide

| Notebook | Role | What it does | Main outputs |
| --- | --- | --- | --- |
| [`01_Heat_Demand_Profiles.ipynb`](01_Heat_Demand_Profiles.ipynb) | **Reference model run** | Calls `gbheatmodel.runner.run_heat_profiles_only()` for a selected weather year, FES dataset/scenario, target year and example grid; visualises thermal demand using `gbheatmodel.HD_Plots`. | Half-hourly, technology-resolved thermal profiles by weather-grid square; optional plots. |
| [`02_COP_and_Electricity_Demand.ipynb`](02_COP_and_Electricity_Demand.ipynb) | **COP and heating-electricity run** | Uses the **same heat-demand settings and runner** as notebook 01, inspects thermal demand, calls `run_cop_profiles()` and `run_electric_demand()`, and checks ASHP/GSHP conversions. | ASHP/GSHP COP series; grid-level heating-related electricity profiles; comparison figures. |
| [`03_National_Demand_Analysis.ipynb`](03_National_Demand_Analysis.ipynb) | **Results analysis** | Reads previously saved thermal and electricity CSVs (does not run the model); aggregates grid-to-GB annual energy and coincident peak; optionally examines exported LA profiles. | Grid, technology and GB summaries, time series, CSV tables and figures. |
| [`04_Local_Authority_Heat_Demand.ipynb`](04_Local_Authority_Heat_Demand.ipynb) | **Stock-informed LA redistribution** | Reads saved thermal grid profiles and redistributes them using the existing `gbheatmodel.LA_heat_profiles` functions, FES heating stocks and LAD 2021 boundaries. Allows one, several or all authorities. | Selected LA half-hourly profiles, annual/peak summaries, conservation audits and maps. |
| [`05_GBHeat_Figures.ipynb`](05_GBHeat_Figures.ipynb) | **Spatial and publication-style figures** | Visualises saved model results, including annual LA/weather-grid maps, peak timing, spatial snapshots, concentration and technology composition. | PNG figures from saved results. |

**One source of truth:** Set the same `weather_year`, `future_year`, `FES_year` and `FES_scenario` in each notebook. Notebook **01** is the reference for these assumptions; **02** generates derived electrical quantities; **03–05** should use saved results from the matching run. Notebook **04** carries out the necessary stock-informed spatial redistribution but **must not change the core heat-demand model**.

## 1. Installation and launch

From the repository root:

```bash
git clone https://github.com/Lavinjafari/GBHeatModel.git
cd GBHeatModel
python -m pip install -e .
python -m pip install jupyterlab ipykernel matplotlib seaborn openpyxl
jupyter lab
```

Select the Python kernel from the environment where `gbheatmodel` was installed. `pyproject.toml` currently declares Python >=3.9 and the base package dependencies, but **does not currently declare** Jupyter, Matplotlib, Seaborn or OpenPyXL. The additional installation line above covers these notebook dependencies; for a reproducible release, record and test a complete environment specification.

The sample commands **install the local package**; no PyPI publication is required. They do **not** download the GBHeat source datasets. See the data section below before executing notebook 01.

## 2. Consistent model configuration

The current notebooks use the following names (examples, not a restriction to this scenario):

```python
weather_year = 2010       # historical meteorological year
future_year = 2050        # target demand year
FES_year = "2022"         # FES data vintage
FES_scenario = "LW"       # pathway; e.g. LW, CT, ST, FS

grid_id = "-3.5_56.0"    # optional grid for inspection
```

The run-folder identifier is:

```python
RUN_ID = f"{weather_year}_{FES_year}_{FES_scenario}_{future_year}"
# Example: 2010_2022_LW_2050
```

- **Notebook 02 only:** choose `performance_level = "current"`, `"good"` or `"very good"` for ASHP and GSHP COP regressions. This does not alter the scenario's thermal-demand assumptions.
- **Notebook 04 only:** choose `method = "fes_stock_area"` (stock–area weighting) or `"fes_stock"` (stock weighting); select LAs by exact name or LAD 2021 code.
- **Notebook 05:** select the same run and LA allocation method as notebook 04 for valid comparisons.

Avoid hard-coded paths specific to one computer. Existing notebooks generally locate data using `gbheatmodel.path.PROJECT_ROOT` or `path_in_data()`.

## 3. Recommended execution order

1. **Prepare input datasets.** Obtain the required FES source data, heating-use-pattern inputs, temperature data, grid geometry and LAD 2021 boundaries and place them at the paths expected by the existing package. The data are not bundled in this Git repository.
2. **Run `01_Heat_Demand_Profiles.ipynb`.** Configure the scenario and generate grid-level thermal demand. The runner remains the authoritative implementation.
3. **Run `02_COP_and_Electricity_Demand.ipynb`** with the **identical four thermal settings** and the chosen COP performance level. It may recalculate the thermal profiles before deriving COP/electricity; this is intentional in the present notebook.
4. **Run `04_Local_Authority_Heat_Demand.ipynb`** when LA profiles are needed; it reads saved thermal grid profiles, generates the full stock-informed LA allocation and exports the selected authorities.
5. **Run `03_National_Demand_Analysis.ipynb`** to analyse saved thermal/electrical outputs. To include LA results, set `LA_PROFILE_FOLDER` to the `profiles/` directory created by notebook 04; its present default `None` skips this section.
6. **Run `05_GBHeat_Figures.ipynb`** against the matching saved run. Complete LA-versus-weather-grid maps require **all** LA profiles, not just one selected LA.

Notebook 03 can be run before notebook 04 for grid/GB analysis; the order above is recommended when all geographical scales are required.

## 4. LA selection and scientific integrity

Notebook 04 **retains the stock-informed `LA_HD_Profile` methodology**. It does not substitute simple area-only division of grid heat demand.

```python
LA_SELECTION = "Perth and Kinross"
# or
LA_SELECTION = ["Perth and Kinross", "City of Edinburgh"]
# or
LA_SELECTION = "all"

method = "fes_stock_area"  # or "fes_stock"
```

The notebook first builds the redistribution for **the complete set of LAs** and checks its conservation; **only then** does it filter the profiles for export. Selecting one authority must not cause all grid demand to be reassigned to that authority.

For the LAD December 2021 GB geography used in this project, expect **363 distinct LA codes**. Check both coverage and key identity (`LAD21CD`), not just the number of profiles. The notebook's conservation diagnostics compare the **sum of all redistributed LAs** with the original grid-level demand **by heating technology and by half-hour**. Selected-authority totals generally do not equal the GB total.

Interpret small positive/negative conservation residuals at floating-point precision as numerical effects, subject to the configured tolerance; report substantive unmatched or unallocated demand rather than silently dropping it. LA outputs are **stock-informed redistributions of gridded modelled demand**, not exact recovery of the model's original LA input shares.

## 5. Data inputs and output directories

The **current package paths** are preserved here for compatibility. Do not move input files into a new `raw/` / `processed/` hierarchy until the package paths have been audited and updated.

### Inputs currently referenced

```text
data/
├── UK_Atlite_Grid_sq.gpkg
├── LAs_shapefile_2021/
│   └── LAD_DEC_2021_GB_BFC.shp  # plus accompanying shapefile components
├── FES_Spatial_Heat_Model/      # FES local authority heating-stock data
├── heat_demand_profiles_patterns/
├── air_temp/
│   └── average_day_air_temp_<weather_year>.csv
└── normalised_half_hourly_profiles.xlsx  # referenced by some visualisations
```

Additional dependencies may be required by the model's preprocessing modules. The repository must eventually document the **source URL, vintage, licence, extraction/processing procedure and expected checksums or schema** for each required input. Large or restricted datasets are intentionally not included.

### Model-generated outputs

```text
data/outputs/
├── heating_profiles/<RUN_ID>/
│   └── half_hourly_heat_profile_<grid_id>*.csv
├── COP_Profiles/
│   ├── ASHP_<performance_level>_<weather_year>_<future_year>.csv
│   └── GSHP_<performance_level>_<weather_year>_<future_year>.csv
├── electric_demand/<RUN_ID>/
│   └── elec_demand_<grid_id>_<FES_year>_<scenario>_<future_year>.csv
├── LA_heat_profiles/<RUN_ID>/<allocation_method>/
│   ├── profiles/LA_heat_profile_<LAD21CD>.csv
│   ├── selected_LA_annual_peak_summary.csv
│   ├── selected_LA_lookup.csv
│   ├── conservation_by_technology.csv
│   ├── unallocated_demand_by_timestep_and_technology_kWh.csv
│   ├── grid_weight_audit.csv
│   └── run_manifest.json
└── figures/<RUN_ID>/
    ├── 02_COP_and_Electricity_Demand/
    ├── 03_National_Demand_Analysis/
    ├── 04_Local_Authority_Heat_Demand/<allocation_method>/
    └── 05_GBHeat_Figures/
```

Some existing `gbheatmodel.HD_Plots` functions instead save optional plots under `data/outputs/plots/<subfolder>/`. Both are generated output locations and **should remain untracked**. `HD_Plots.py` currently contains a duplicate definition of `plot_boxplot_half_hourly_distribution`; the later definition overrides the earlier, so its `save` option will not operate as documented until this is fixed. It also includes hard-coded 2050 dates in some helpers. These are **future code-maintenance items**, not reasons to change model outputs for this documentation commit.

### Units and peak definitions

| Quantity | Conversion from source GBHeat profiles |
| --- | --- |
| Half-hourly thermal/electrical energy | **kWh per 30-minute interval** |
| Annual energy in GWh | `sum(kWh) / 1e6` |
| Annual energy in TWh | `sum(kWh) / 1e9` |
| Mean power for each half-hour in MW | `kWh_per_half_hour * 2 / 1000` |
| Mean power for each half-hour in GW | `kWh_per_half_hour * 2 / 1e6` |

A **local grid peak** is each grid cell's maximum at its own timestep. The **GB coincident peak** is the maximum of the national sum at one common timestep. The sum of all local maxima is **not** the GB coincident peak.

The electricity-demand code currently covers ASHP, GSHP and three hybrid technologies. This is **heating-related electricity demand for the technologies implemented**, not the GB electricity system's total demand and not every electrical heating technology.

## 6. Generating figures

Notebook 05 is intended to preserve the map framing and panel styling of `GBHeat_paper_plots.ipynb` while reading saved results. Useful figure groups include:

- Annual domestic heat demand across LAD 2021 and Atlite weather-grid resolutions.
- Full-year timing separation between local peaks and the GB coincident peak.
- Maximum heating demand by Atlite grid square.
- Spatial demand snapshots immediately before, at and after the GB peak.
- Local-peak versus coincident-peak concentration.
- National thermal demand by heating technology.

**Release caveat:** The various plotting versions used during notebook refactoring have not yet been demonstrated to be identical on an executed dataset. Validate the committed `05_GBHeat_Figures.ipynb` visually against the original publication plots, check axis units and map extent, and ensure its save paths all use `data/outputs/figures/` before declaring it production-ready.

## 7. Keeping GitHub lightweight

**Never commit simulation results just to demonstrate the notebooks.** Outputs should be regenerated from documented inputs. For a public release, distribute at most a small, appropriately licensed sample dataset and provide acquisition/preprocessing instructions for the complete inputs.

The current root `.gitignore` contains a broad `data/` rule. This successfully hides local datasets, **but also hides any new `data/README.md` or sample inputs**. When preparing the data-management release, either narrowly ignore large data paths while explicitly allowing documentation/examples, or add a one-off tracked file intentionally. Do not use `git add -f data/` indiscriminately. `gitignore` rules do not untrack files that Git already tracks.

## 8. Troubleshooting and pre-release checklist

- **`ModuleNotFoundError: gbheatmodel`** — install the local package from the repository root with `python -m pip install -e .` in the active Jupyter environment.
- **Missing input files** — check actual data paths against `gbheatmodel.path` and the runner's input requirements, not a notebook-specific copied path.
- **Missing thermal/electric CSVs** — ensure notebooks 01/02 completed with matching `RUN_ID` settings; generation in memory does not always imply a CSV was saved, so inspect the output folder.
- **LA analysis skipped in notebook 03** — explicitly set `LA_PROFILE_FOLDER` to the validated notebook 04 `profiles/` directory.
- **Incomplete LA map in notebook 05** — set `LA_SELECTION = "all"` in notebook 04 and export every LA profile for the same run and method.
- **Conservation check fails** — inspect `conservation_by_technology.csv`, unallocated demand and `grid_weight_audit.csv`; do not suppress failures.
- **Before public release** — run all five notebooks in fresh kernels, check scientific units and outputs, confirm the required third-party input licences, ensure all generated outputs are ignored and record the tested dependency versions.

For model architecture and scientific details, see the [repository README](../README.md) and the source code in [`src/gbheatmodel`](../src/gbheatmodel).
