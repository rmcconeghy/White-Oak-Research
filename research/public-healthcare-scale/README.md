# Analysis 03 · Who pays for American healthcare?

Version 2.0 replaces the four-panel program comparison at `analyses/public-healthcare-scale/`. The public page and assets are under `site/` in the local project. In the White Oak Research repository the public files live directly at the existing route, and the source workspace lives at `research/public-healthcare-scale/`.

## Rebuild

From this source workspace, run Python 3 and librsvg’s `rsvg-convert`:

```sh
python3 scripts/build_mix_data.py
python3 scripts/build_mix_figures.py
```

In the GitHub repository, pass `--site ../../analyses/public-healthcare-scale` to both commands when running them from `research/public-healthcare-scale/`. The transformation requires only the Python standard library. The figure script writes responsive SVGs and rasterizes the three hero editions at 2×. The public HTML and CSS are static, with no build step for GitHub Pages.

## Pinned inputs

- `data/raw/cms-detail.zip` contains the complete [CMS source-of-funds historical CSV](https://www.cms.gov/files/zip/national-health-expenditures-type-service-source-funds-cy-1960-2024.zip). The first section is the all-services total and funding breakdown.
- `data/raw/cms-summary.zip` contains the [same-release CMS Table 1 summary](https://www.cms.gov/files/zip/nhe-summary-including-share-gdp-cy-1960-2024.zip), including rounded national health expenditures and the GDP denominator.
- `data/raw/bea-gdp-deflator-2026-10-29.csv` is the annual GDP implicit price deflator (NIPA 1.1.9, line 1, A191RD) from the October 29, 2026 [BEA Section 1 workbook](https://apps.bea.gov/national/Release/XLS/Survey/Section1All_xls.xlsx). The original workbook is archived in the local project. To regenerate the compact extract, place the original workbook at `data/raw/bea-section1.xlsx` and run `python3 scripts/extract_mix_prices.py`. The report includes the original workbook hash and the hashes of all three inputs used by the build. The BEA release URL can roll to a newer vintage.

The methods page defines the accounting categories and documents the reconciliation and rounding. The CSV uses one row per year with explicit dollar units, the complete set of components, and the rounding adjustment for Other. The validated CMS 2024 source rows are also preserved in the report.

## Publication assets

The desktop hero pairs the stack with directly labeled 2024 amounts. The compact edition moves the amounts into the legend for a narrower viewport. The 1200 × 1500 LinkedIn edition has a portrait composition with a larger two-line headline, an integrated 2024 key, and source notes. All editions retain the same stack order and colors. Repo history and the original local project archive preserve Version 1.
