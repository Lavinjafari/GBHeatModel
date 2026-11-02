# GBHeat — Notebooks

Practical examples for running and analysing **GBHeat**, the Great Britain residential heat-demand model. Notebooks 01–05 primarily use the existing `gbheatmodel` Python package under `src/` and saved model outputs. Notebook 06 is an optional custom-scenario example: it uses package scenario-alignment functions and explicitly reproduces the RHPP/Watson total-heat calculation because the supplied legacy custom-scenario function is not directly executable.

> **Status:** These notebooks are being prepared for a public release. All six notebooks still require fresh-environment, end-to-end testing with the appropriate model inputs. Validate notebook 05 against the reference paper figures and notebook 06 against the original benchmark visuals before tagging a release.

## Notebook guide

| Notebook | Role | What it does | Main outputs |
| --- | --- | --- | --- |
| [`01_Heat_Demand_Profiles.ipynb`](01_Heat_Demand_Profiles.ipynb) | **Reference model run** | Calls `gbheatmodel.runner.run_heat_profiles_only()` for a selected weather year, FES dataset/scenario, target year and example grid; visualises thermal demand using `gbheatmodel.HD_Plots`. | Half-hourly, technology-resolved thermal profiles by weather-grid square; optional plots. |
| [`02_COP_and_Electricity_Demand.ipynb`](02_COP_and_Electricity_Demand.ipynb) | **COP and heating-electricity run** | Uses the **same heat-demand settings and runner** as notebook 01, inspects thermal demand, calls `run_cop_profiles()` and `run_electric_demand()`, and checks ASHP/GSHP conversions. | ASHP/GSHP COP series; grid-level heating-related electricity profiles; comparison figures. |
| [`03_National_Demand_Analysis.ipynb`](03_National_Demand_Analysis.ipynb) | **Results analysis** | Reads previously saved thermal and electricity CSVs (does not run the model); aggregates grid-to-GB annual energy and coincident peak; optionally examines exported LA profiles. | Grid, technology and GB summaries, time series, CSV tables and figures. |
| [`04_Local_Authority_Heat_Demand.ipynb`](04_Local_Authority_Heat_Demand.ipynb) | **Stock-informed LA redistribution** | Reads saved thermal grid profiles and redistributes them using the existing `gbheatmodel.LA_heat_profiles` functions, FES heating stocks and LAD 2021 boundaries. Allows one, several or all authorities. | Selected LA half-hourly profiles, annual/peak summaries, conservation audits and maps. |
| [`05_GBHeat_Figures.ipynb`](05_GBHeat_Figures.ipynb) | **Spatial and publication-style figures** | Visualises saved model results, including annual LA/weather-grid maps, peak timing, spatial snapshots, concentration and technology composition. | PNG figures from saved results. |
| [`06_Custom_Scenario_and_Benchmark_Comparison.ipynb`](06_Custom_Scenario_and_Benchmark_Comparison.ipynb) | **Optional custom scenario and benchmarking** | Aligns user-defined dwelling stocks and technology shares, generates RHPP/Watson total-thermal profiles with an insulation factor, and plots custom and optional FES pathway peak days against supplied Watson/Sansom benchmark CSVs. | Custom-grid profiles, scaled stock tables, national time series, scenario manifest, peak summary and benchmark PNGs. |

**One source of truth for the standard FES pathway:** Set the same `weather_year`, `future_year`, `FES_year` and `FES_scenario` in notebooks 01–05. Notebook **01** is the reference; **02** generates derived electrical quantities; **03–05** consume saved matching results, and **04** carries out the necessary stock-informed LA redistribution. **06** is an independent optional *custom RHPP total-heat* workflow and has its own scenario name, dwelling total, technology-stock shares and insulation factor. Do not interpret notebook 06 results as a technology-specific FES scenario.

## 1. Installation and launch

From the repository root:

```bash
git clone https://github.com/Lavinjafari/GBHeatModel.git
cd GBHeatModel
python -m pip install -e ".[notebooks]"
jupyter lab
```

Select the Python kernel from the environment where `gbheatmodel` was installed. The revised `pyproject.toml` includes a `[project.optional-dependencies]` group named `notebooks` (JupyterLab, ipykernel, Matplotlib, Seaborn, OpenPyXL and Shapely). For scientific reproducibility, record and test an environment lock or fully specified dependency versions before release.

The sample commands **install the local package**; no PyPI publication is required. They do **not** download externally hosted ERA5, air-temperature or heating-pattern datasets. See the data section below before executing notebook 01.

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
- **Notebook 06 (optional):** configure `WEATHER_YEAR`, `FUTURE_YEAR`, `SCENARIO_NAME`, `TOTAL_DWELLINGS`, `TECHNOLOGIES`, `TECH_SHARES`, `INSULATION_IMPROVEMENT` and `RHPP_SHARES`. Use `FES_YEAR` and `COMPARE_FES_SCENARIOS` only to locate optional existing standard-pathway outputs for comparison. The custom run ID is `f"{WEATHER_YEAR}_{SCENARIO_NAME}_{FUTURE_YEAR}"`, **not** the standard four-part FES run ID.

Avoid hard-coded paths specific to one computer. Existing notebooks generally locate data using `gbheatmodel.path.PROJECT_ROOT` or `path_in_data()`.

## 3. Recommended execution order

1. **Prepare input datasets.** Clone the repository for its tracked, redistributable model inputs, then obtain externally hosted ERA5/Atlite, air-temperature and heating-pattern datasets and place them in the existing expected directories. An automatic Zenodo downloader is planned but is not yet provided here.
2. **Run `01_Heat_Demand_Profiles.ipynb`.** Configure the scenario and generate grid-level thermal demand. The runner remains the authoritative implementation.
3. **Run `02_COP_and_Electricity_Demand.ipynb`** with the **identical four thermal settings** and the chosen COP performance level. It may recalculate the thermal profiles before deriving COP/electricity; this is intentional in the present notebook.
4. **Run `04_Local_Authority_Heat_Demand.ipynb`** when LA profiles are needed; it reads saved thermal grid profiles, generates the full stock-informed LA allocation and exports the selected authorities.
5. **Run `03_National_Demand_Analysis.ipynb`** to analyse saved thermal/electrical outputs. To include LA results, set `LA_PROFILE_FOLDER` to the `profiles/` directory created by notebook 04; its present default `None` skips this section.
6. **Run `05_GBHeat_Figures.ipynb`** against the matching saved run. Complete LA-versus-weather-grid maps require **all** LA profiles, not just one selected LA.
7. **Optional alternative:** Run **`06_Custom_Scenario_and_Benchmark_Comparison.ipynb`** to create a user-defined RHPP/Watson *total thermal* scenario. It uses the tracked `data/Scenario_Alignment/heat_techs_distribution_grid_square.csv`, requires the external half-hourly pattern CSVs, and does not require notebooks 01–05 to have executed unless you also want standard FES pathway comparisons. Supply the actual digitised Watson/Sansom benchmark CSVs to display their lines.

Notebook 03 can be run before notebook 04 for grid/GB analysis; the order above is recommended when all geographical scales are required. Notebook 06 is a separate optional branch, not a replacement for notebook 01.

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

## 5. Custom scenario alignment and benchmark comparison (Notebook 06)

Notebook 06 provides a user-friendly workflow for custom **RHPP/Watson total thermal demand** scenarios, adapted from `half_hourly_profile_costumed_scenario.py` and the original `Validation_3.ipynb` benchmark visualisation.

### Configure a custom run

```python
WEATHER_YEAR = 2010
FUTURE_YEAR = 2050
SCENARIO_NAME = "Watson_custom"
TOTAL_DWELLINGS = 25_800_000
INSULATION_IMPROVEMENT = 1.0
TECHNOLOGIES = ["ASHP", "GSHP"]
TECH_SHARES = [0.75, 0.25]
RHPP_SHARES = {"daytime": 0.28, "bi-modal": 0.08, "continuous": 0.64}

# Optional comparison against saved standard FES runs
FES_YEAR = "2022"
COMPARE_FES_SCENARIOS = ["LW"]
WATSON_BENCHMARK_CSV = None
SANSOM_BENCHMARK_CSV = None
```

1. Read `data/Scenario_Alignment/heat_techs_distribution_grid_square.csv` without modifying the source file.
2. Apply the package's `scale_FES_dwellings()` and `assign_tech_shares()` to create and save aligned stock tables.
3. Read the external `data/heat_demand_profiles_patterns/HD_heat_patterns_<WEATHER_YEAR>/` files and build a half-hourly total-heat profile for each grid. The model multiplies the RHPP-weighted daytime, bi-modal and continuous patterns by each grid's dwelling count and the insulation factor.
4. Save the custom grid profiles and a manifest of scenario parameters, then aggregate their national half-hourly demand.
5. Produce the original-style 12 × 6-inch peak-day comparisons with any supplied Watson/Sansom data; optionally add standard FES scenario outputs if already generated.

**Interpretation and limitations:** The technology shares specify **stock alignment**, but the implemented RHPP total-demand calculation uses only the total dwelling number per grid, weather-driven pattern and insulation multiplier. Altering ASHP/GSHP shares alone **does not** alter the plotted total thermal demand. Notebook 06 reproduces the active legacy function's scientific expression inside the notebook because that source function depends on undefined globals and obsolete paths; it is not a claim to call a fully operational custom-runner API. Both weather and target years must be non-leap years in the present 17,520-half-hour implementation. The chosen peak day maximises **national daily energy**, which need not be the day containing the largest individual half-hour. Benchmark CSVs are optional and are **not** shipped or synthesized by this notebook.

## 6. Data inputs and output directories

The **current package paths** are preserved here for compatibility. Do not move input files into a new `raw/` / `processed/` hierarchy until the package paths have been audited and updated.

### Inputs currently referenced

```text
data/
├── UK_Atlite_Grid_sq.gpkg
├── LAs_shapefile_2021/
│   └── LAD_DEC_2021_GB_BFC.shp  # plus accompanying shapefile components
├── FES_Spatial_Heat_Model/      # FES local authority heating-stock data
├── Scenario_Alignment/
│   └── heat_techs_distribution_grid_square.csv
├── spatial_operators/
├── heat_demand_profiles_patterns/
├── air_temp/
│   └── average_day_air_temp_<weather_year>.csv
└── normalised_half_hourly_profiles.xlsx  # referenced by some visualisations
```

The GitHub data policy tracks suitable model inputs (including FES spatial inputs, LAD 2021 boundaries, scenario alignment and small spatial operators), while **`data/Atlite/`, `data/air_temp/` and `data/heat_demand_profiles_patterns/`** are excluded because of their size and are intended for external Zenodo distribution. `data/outputs/` and temporary large archives remain local. Additional preprocessing dependencies may exist. Record the **source URL/DOI, vintage, licence, extraction procedure, data schema and checksums** before the public release; do not assume that every upstream dataset permits redistribution.

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

# Optional custom RHPP scenario outputs:
data/outputs/
├── Scenario_Alignment_Outputs/<CUSTOM_RUN_ID>/
│   ├── scaled_dwellings.csv
│   ├── custom_technology_stocks.csv
│   ├── national_half_hourly_heat.csv
│   ├── peak_day_comparison.csv
│   └── scenario_manifest.json
├── heating_profiles/heating_profiles_custom/<CUSTOM_RUN_ID>/
│   └── half_hourly_HD_<grid_id>_<scenario>_<weather_year>_<future_year>.csv
└── figures/<CUSTOM_RUN_ID>/06_Custom_Scenario/
    ├── custom_vs_benchmarks_<CUSTOM_RUN_ID>.png
    └── all_scenarios_vs_benchmarks_<CUSTOM_RUN_ID>.png
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

## 7. Generating figures

Notebook 05 is intended to preserve the map framing and panel styling of `GBHeat_paper_plots.ipynb` while reading saved results. Useful figure groups include:

- Annual domestic heat demand across LAD 2021 and Atlite weather-grid resolutions.
- Full-year timing separation between local peaks and the GB coincident peak.
- Maximum heating demand by Atlite grid square.
- Spatial demand snapshots immediately before, at and after the GB peak.
- Local-peak versus coincident-peak concentration.
- National thermal demand by heating technology.

Notebook **06** retains the requested benchmark plot proportions and line conventions from `Validation_3.ipynb`, including 12 × 6-inch panels, 2-point custom/FES lines, 3-point dash-dot Sansom and dashed Watson curves, and output at 600 dpi. Its comparison plots show each scenario on its own daily-energy-maximum day, not a necessarily shared calendar date.

**Release caveat:** The various plotting versions used during notebook refactoring have not yet been demonstrated to be identical on an executed dataset. Validate the committed `05_GBHeat_Figures.ipynb` visually against the original publication plots, check axis units and map extent, and ensure its save paths all use `data/outputs/figures/` before declaring it production-ready.

## 8. Keeping GitHub lightweight

**Never commit simulation results just to demonstrate the notebooks.** Outputs should be regenerated from documented inputs. For a public release, distribute at most a small, appropriately licensed sample dataset and provide acquisition/preprocessing instructions for the complete inputs.

The revised root `.gitignore` **does not exclude all of `data/`**. It selectively ignores `data/outputs/`, `data/Atlite/`, `data/air_temp/`, `data/heat_demand_profiles_patterns/` and named large temporary archives while allowing curated input files and `data/README.md` to be committed. Git ignores do not untrack files already committed. Distribute the large external inputs through versioned Zenodo deposits and preserve their expected local folder names.

## 9. Troubleshooting and pre-release checklist

- **`ModuleNotFoundError: gbheatmodel`** — install the local package from the repository root with `python -m pip install -e .` in the active Jupyter environment.
- **Missing input files** — check actual data paths against `gbheatmodel.path` and the runner's input requirements, not a notebook-specific copied path.
- **Missing thermal/electric CSVs** — ensure notebooks 01/02 completed with matching `RUN_ID` settings; generation in memory does not always imply a CSV was saved, so inspect the output folder.
- **LA analysis skipped in notebook 03** — explicitly set `LA_PROFILE_FOLDER` to the validated notebook 04 `profiles/` directory.
- **Incomplete LA map in notebook 05** — set `LA_SELECTION = "all"` in notebook 04 and export every LA profile for the same run and method.
- **Conservation check fails** — inspect `conservation_by_technology.csv`, unallocated demand and `grid_weight_audit.csv`; do not suppress failures.
- **Notebook 06 cannot find inputs** — confirm `Scenario_Alignment/heat_techs_distribution_grid_square.csv` exists, download the correct weather-year heating patterns, and set benchmark CSV paths if benchmark curves are needed.
- **Notebook 06 does not change total heat when technology shares change** — expected for this RHPP total-heat implementation; technology stocks are exported independently.
- **Notebook 06 refuses a leap year** — its source calculation currently assumes 17,520 half-hour intervals.
- **Before public release** — run all six notebooks in fresh kernels, check scientific units and outputs, confirm the required third-party input licences, ensure all generated outputs are ignored and record the tested dependency versions.

For model architecture and scientific details, see the [repository README](../README.md) and the source code in [`src/gbheatmodel`](../src/gbheatmodel).
