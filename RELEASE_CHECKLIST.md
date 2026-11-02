# GBHeat research-software release audit

**Basis:** User-supplied `GBHeatModel-main.zip`, manuscript PDF and six figure images, inspected 2 November 2026. This is a *static* audit; the full notebooks were not executed with external datasets.

## Verified gaps in the supplied repository archive

| Area | Observation | Priority / action |
|---|---|---|
| Root README | Existing root `README.md` contains only `# Spatiotemporal-Domestic-Heat-Demand-Modelling` | **Critical:** replace with the supplied research-software README |
| External datasets | Large input directories excluded; no verified Zenodo DOI/download module in archive | **Critical:** publish/version data with checksums, paths and provenance |
| Licence | No top-level `LICENSE` file found | **Critical:** choose an appropriate software licence with author/institution agreement; audit ONS/FES/Watson data redistribution separately |
| Tests | No test suite/test directory found | **High:** add smoke tests, stock conservation, timeseries units, and benchmark regression checks |
| Notebooks | Six notebooks exist; full fresh-environment execution not confirmed | **High:** run in clean kernels and compare plots against paper |
| Paper geography | Manuscript claims 371 Local Authorities; Notebook 04 and supplied LAD2021 boundaries use 363 | **High:** reconcile source geographies and clarify scope in paper + README |
| Dependencies | `pyproject.toml` contains notebook extras, but two conda files and built egg-info are also present | **Medium:** consolidate tested environments and confirm reproducible installation |
| Repository hygiene | ZIP includes a populated `Notebooks/.ipynb_checkpoints` directory and `src/gbheatmodel.egg-info` although current `.gitignore` excludes them | **Medium:** check which are genuinely tracked with `git ls-files`; if tracked, remove from Git index without deleting local working copies |
| Code/paths | `path.py` includes `ATILITE` and `LAs_shapefiles_2021` constants with spellings not matching actual input directory names; `OUTPUTS_DIR` points to root `outputs` whereas the runner uses `data/outputs` | **High:** audit callers; fix only after tests and avoid altering numerical results |
| Notebook 06 | Custom RHPP total-heat path had a schema mismatch during development; static code only not full execution verified | **High:** confirm full custom scenario, conserved stock counts, saved profiles and benchmark figures |
| Scientific scope | Core model represents combined space heat + DHW; electrification code includes only supported HP/hybrid categories | **Medium:** state limitations consistently; don't claim all 14 electric loads are calculated |
| Citation | No `CITATION.cff` or published paper DOI verified in the archive | **Medium:** add after author-approved bibliographic metadata and release DOI exist |
| Figures | Paper figures provided separately, but no versioned `docs/figures/` existed | **Medium:** copy supplied originals (included in this documentation pack) and credit them |

## Suggested release gates (before a v1.0 tag)

- [ ] Adopt suitable licence, obtain author/institution approval, audit redistribution and attribution for FES/ONS/Watson-derived datasets.
- [ ] Publish Zenodo input archive(s) with DOI, dataset version, checksum manifest, `data/` extraction layout, and tested retrieval instructions.
- [ ] Install into fresh environment; run notebooks 01–06 (optionally use smaller test scenario) and retain execution logs.
- [ ] Add automated shape, stock balance, time-index, unit, geographic coverage and conservation assertions.
- [ ] Reproduce key manuscript benchmark metrics and compare all major plot visuals with originals.
- [ ] Resolve 371 vs 363 LAD discrepancy and document administrative boundary version.
- [ ] Review old path constants and ensure every output goes under ignored `data/outputs/`.
- [ ] Track exactly the appropriate project datasets; inspect `.ipynb_checkpoints/` and egg-info tracking status.
- [ ] Create GitHub Release with pinned commit, changelog and paper/data citations.

## Safe local installation and staging

Copy the pack contents into the existing repository, retaining relative paths. Inspect with `git status` and `git diff`; stage only the four documentation/assets areas: `README.md`, `data/README.md`, `docs/figures/`, `RELEASE_CHECKLIST.md`. These files do **not** alter the model code, calculations or existing notebook plotting functions.

```
git add README.md data/README.md docs/figures RELEASE_CHECKLIST.md
git diff --cached --stat
git diff --cached --check
git commit -m "docs: introduce GBHeat research software and reproducibility guide"
git push origin main
```

Do not publish a formal release merely because the README has been improved; complete the critical release gates first.
