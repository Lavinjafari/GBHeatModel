# GBHeat — FES 2021/2022/2024/2025 reader update

This patch replaces exactly two modules in `src/gbheatmodel/` and adds a regression test. It **does not change** the heat-demand or COP algorithms.

## Files to copy

- `src/gbheatmodel/FES_heat_supply_data.py`
- `src/gbheatmodel/FES_scaling_factor.py`
- `tests/test_fes_releases.py`

Keep the rest of your existing package unchanged. The test script uses `data/FES_Spatial_Heat_Model/` in your repository.

## Source data supported

| FES vintage | Spatial-stock years | Accepted internal codes (new codes are GBHeat-defined aliases) |
|---|---|---|
| 2021 | 2020, 2025, 2030, 2035 | CT, LW, SP, ST |
| 2022 | 2020, 2025, 2030, 2035, 2040, 2045, 2050 | CT, LW, FS, ST |
| 2024 | 2020, 2025, 2030, 2035, 2040, 2045, 2050 | EE, HT, HE, CF |
| 2025 | 2025, 2030, 2035, 2040, 2045, 2050 | EE, HT, HE, FB |

Full names (e.g. `Electric Engagement`, `Holistic Transition`, `Hydrogen Evolution`, `Counterfactual` and `Falling Behind`) work as well as the codes. Old codes are **not mapped** to new, non-equivalent pathways.

`year_FES_heat_supply(2037, "2024", "HT")` uses the **2035** stock file (previous documented nearest-prior-year rule). `year_FES_heat_supply(2020, "2025", "HT")` raises an informative error, since that vintage has no 2020 stock file. The 2025 **annual heat-demand** table nevertheless contains a historic 2020 baseline for scaling, so this is not a conflict.

## Examples

```python
from gbheatmodel.FES_heat_supply_data import (
    available_FES_scenarios, available_FES_years,
    year_FES_heat_supply, read_FES_heat_supply,
)
from gbheatmodel.FES_scaling_factor import FES_scaling_factor_calc

print(available_FES_scenarios("2024"))
print(available_FES_years("2025"))
stock_2024 = year_FES_heat_supply(2050, "2024", "Electric Engagement")
stock_2025 = year_FES_heat_supply(2050, "2025", "HT")
scaling_2024 = FES_scaling_factor_calc(2050, "2024", "EE")
scaling_2025 = FES_scaling_factor_calc(2050, "2025", "Holistic Transition")
```

The default LA index remains `Local_Authority`. The newer `Pathway` field is preserved, while `Scenario` contains a GBHeat-defined short code and `CODE_x` provides the same LA-code column expected by legacy processing functions. Every returned year has 14 explicit numeric stock fields; the old FES sources can contain missing hydrogen fields and NA values, both normalised to zero as in the legacy concatenated reader.

## **Scientific compatibility requiring an additional step**

These updated modules correctly **load** FES 2024 and 2025, but are **not an end-to-end assertion that the existing model runner supports them**:

1. **FES 2024: Biofuel versus BioLPG.** `stock Biofuel boiler` and `stock Hybrid (ASHP + Biofuel boiler)` are intentionally preserved. The existing `tech_half_hourly_profile.py` expects `BioLPG` labels and would silently assign zero stock to unmatched keys. Do not equate these fuels without a documented modelling decision. Update downstream validation and technology coefficients before using a 2024 run as published scientific evidence.
2. **FES 2025: Communal/district heat labels.** `stock Fossil fuel communal heating` and `stock Low carbon district heating` are exposed through the historical schema aliases `stock Community` and `stock DH`. This is a dataset-label adaptation and must be documented in resulting plots, not treated as evidence of unchanged technology assumptions.
3. **Downstream position-based selection.** Existing `heat_tech_distribution.py` uses expressions such as `df.columns[13:]`. These are fragile when the FES 2024/2025 schemas add `Pathway` or change stock-column order. Replace them with explicit `stock ` technology selection (and then strip the prefix in one clear step) in a separate, validated patch. The legacy `FES_shapefile_LAs_matching.py` also expects 2021 boundaries and has older LA aggregation logic; test LA conservation and correct names against each vintage.
4. **FES heat scaling.** The annual-demand CSV data are read as provided. The model still applies annual residential-demand ratios to half-hourly heat profiles; unchanged scientific methodology.

## Validation completed

`pytest -q tests/test_fes_releases.py` — 10 tests passed against the full supplied archive; tested scenarios, years, selected rows, missing historical technologies, FES 2024 Biofuel, FES 2025 district/communal labels and annual scaling. No full GBHeat pipeline or numerical model-output equivalence test has been executed.
## NESO technology-name alignment — October 2026

GBHeat supports FES spatial heating-technology stock datasets from the 2021, 2022, 2024 and 2025 releases.

On 28 October 2026, NESO announced updates to historical spatial heat dataset column identifiers for hybrid heating technologies. The revised identifiers use the form `Hybrid ASHP and [technology]` instead of `Hybrid (ASHP + [technology])`, affecting `stock` and `stock_proportion` fields.

**Official source:** [NESO — Local Authority Level Spatial Heat Model Outputs (FES)](https://www.neso.energy/data-portal/local-authority-level-spatial-heat-model-outputs-fes)

### Technology-name harmonisation

| Updated NESO name | GBHeat internal name |
|---|---|
| Hybrid ASHP and Biofuel boiler | Hybrid (ASHP + Biofuel boiler) |
| Hybrid ASHP and BioLPG boiler | Hybrid (ASHP + BioLPG boiler) |
| Hybrid ASHP and Hydrogen boiler | Hybrid (ASHP + Hydrogen boiler) |
| Hybrid ASHP and Electric resistive | Hybrid (ASHP + Electric resistive) |

The `fes_technology_schema.py` module accepts historical and updated identifiers. `FES_heat_supply_data.py` normalises the source headers when reading the datasets, retaining backward compatibility with the downstream GBHeat modules.

Biofuel and BioLPG technology categories remain distinct. No automatic fuel substitution is performed.

Each selected FES release contains 14 heating-technology stock categories. The technology-pattern library recognises both release-specific Biofuel and BioLPG names, but generated profiles are limited to the 14 technologies present in the selected dataset.

### Validation

For FES 2024 Electric Engagement (2050) and FES 2025 Holistic Transition (2050), the following checks passed:

- Reading 371 original FES Local Authority records and 14 heating-technology columns.
- Harmonising 371 source authorities to 363 authorities aligned with the GBHeat 2021 LA geography.
- Preserving all 14 national technology-stock totals during LA harmonisation.
- Allocating technology stocks to 738 weather-grid cells while conserving national totals.
- Matching all 14 technologies to heating-use-pattern coefficients.
- Testing the Biofuel hybrid electricity calculation with an explicitly supplied 70% ASHP heat share, used for test purposes only.

The existing GBHeat heat-demand equations and heating-use-pattern coefficients were retained.

**Scope limitation:** These checks establish input-schema and spatial-stock compatibility for the tested configurations. Full half-hourly simulations and downstream electricity-demand coverage for all FES pathways have not yet been validated. Standalone electric resistive and storage electricity-demand treatment is outside the scope of this alignment update.

### Historical FES summary columns

FES 2021 and FES 2022 spatial heat outputs contain 16 columns with the `stock ` prefix. However, only 14 represent individual heating technologies.

The additional columns, `stock Total` and `stock TotalHPs`, are aggregate summary variables rather than independent heating technologies. GBHeat excludes these fields from technology-level stock distribution and heating-demand profile generation to avoid double-counting.

FES 2024 and FES 2025 contain 14 individual technology-stock columns without these additional summary fields in the tested datasets.

GBHeat therefore retains a 14-technology modelling framework across all four FES releases, with release-specific treatment of Biofuel and BioLPG technology names.
## Git procedure (PowerShell from the repository root)

```powershell
git status
# Copy the three files above into the corresponding repository paths.
python -m pytest -q tests/test_fes_releases.py
git diff -- src/gbheatmodel/FES_heat_supply_data.py src/gbheatmodel/FES_scaling_factor.py
git add src/gbheatmodel/FES_heat_supply_data.py src/gbheatmodel/FES_scaling_factor.py tests/test_fes_releases.py
git diff --cached --check
git commit -m "feat(fes): support 2024 and 2025 spatial stocks and heat scaling"
git push origin main
```
