# Reproducing the altitude audit

[Project overview](README.md) · [Technical case study](WRITEUP.md)

This guide distinguishes rebuilding from the shareable bundle from comparing against the original research directory. Both routes reuse the curated venue table and retrospective mass cache.

## Data and reproduction

The supported audit runs locally and makes no network requests. It requires these files alongside the scripts:

| Input | Role |
|---|---|
| `dataset_all.csv` | Race history, within-athlete comparisons, and venue-country audit |
| `dataset_v3.csv` | Enriched sample from which eligible model rows are selected |
| `athlete_anthro_cache.json` | Retrospective athlete mass proxies, with country/event fallbacks |

The race archive comes from [World Athletics Database, published by mexwell on Kaggle](https://www.kaggle.com/datasets/mexwell/world-athletics-database). Its data card credits **thomascamminady** and links to the [original repository](https://github.com/thomascamminady/world-athletics-database). On September 30, 2026, Kaggle displayed **version 1**, updated **July 23, 2024**, and **MIT** license metadata.

Download the archive from that Kaggle page and retain the men's and women's CSVs for 100, 200, 400, 800, 1500, 3000, 5000, and 10000 metres under `archive_data/`. [DATA_PROVENANCE.json](DATA_PROVENANCE.json) records row counts and SHA-256 hashes for these 16 local files. A fresh version-1 download on September 30, 2026 matched all 16 files byte-for-byte. The original local download date remains unknown. The displayed license is recorded as publisher metadata.

The CSVs are present in the working research directory but excluded from Git. **A fresh checkout does not contain the complete data.** Input hashes in the saved audit identify the derived analysis snapshot. Venue enrichment and mass proxies are separate inputs; downloading the Kaggle archive alone does not reproduce the enriched CSVs.

The verified ingestion route is `build_dataset_archive.py` followed by `enrich_v3.py`, using the event/sex archive CSVs and the existing curated venue table. The fresh-download check deliberately omits separately scraped indoor data, which the supported audit excludes. Other scrapers and weather-enrichment experiments remain historical tooling.

The audit was exercised with Python 3.8.12 and the pinned packages in `requirements.txt`. These record the available research environment, not a recommendation for a new deployment. With a compatible Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

If the required data files already exist, run the audit with a separate output path to preserve the saved report. Otherwise, follow “Rebuild from the bundle” below first:

```bash
OPENBLAS_NUM_THREADS=1 python reproduce.py --output /tmp/track-altitude-audit.json
```

No sibling checkout of `unfolds` or `potage` is needed for this audit. Historical experiments using those libraries remain in the repository.

## Rebuild from the bundle

The ZIP includes the supported scripts, auxiliary inputs, tests, and saved reports; race CSVs are excluded. After setting up the Python environment above, download the version-1 archive:

```bash
curl --fail --location --output /tmp/track-altitude-fresh.zip \
  'https://www.kaggle.com/api/v1/datasets/download/mexwell/world-athletics-database?datasetVersionNumber=1'
```

Extract the 16 event/sex CSVs listed in `DATA_PROVENANCE.json` into `archive_data/`, preserving their filenames, then run:

```bash
python build_dataset_archive.py
python enrich_v3.py
OPENBLAS_NUM_THREADS=1 python reproduce.py --output /tmp/rebuilt-audit.json
```

Optional indoor scrapes can remain absent. This builds the analysis without the original derived CSVs or a sibling `unfolds` or `potage` checkout.

## Fresh-download verification

**Passed on September 30, 2026.** [The saved report](results/fresh_download.json) records:

- All **16/16** selected source files match the local archive SHA-256 hashes.
- All **170,814 outdoor race records** and **96,294 enriched outdoor records** match, including duplicate counts and every column.
- The **93,990-row analysis**, all temporal-fold metrics and coefficients, overlap checks, and career-support results reproduce exactly, with no numerical tolerance.

**This comparison route requires the original local archive files and reference `dataset_all.csv` / `dataset_v3.csv`, which are not in the bundle.** To rebuild from the bundle alone, use the preceding section.

With those reference files available, repeat the check with a fresh version-1 archive:

```bash
curl --fail --location --output /tmp/track-altitude-fresh.zip \
  'https://www.kaggle.com/api/v1/datasets/download/mexwell/world-athletics-database?datasetVersionNumber=1'
python verify_fresh_download.py --archive /tmp/track-altitude-fresh.zip
```

The verifier builds in a new temporary directory and writes `results/fresh_download.json`; use `--output /tmp/fresh-check.json` to preserve the saved report. It exits nonzero on a mismatch. It never copies the old derived race CSVs into the build. The fresh full CSV hashes differ because optional indoor rows are omitted; their outdoor records match exactly.

This verifies a fresh **race-data rebuild**, using the existing venue table, retrospective mass cache, and Python environment. It does not independently remeasure those auxiliary inputs or test installation in a new environment. The original datasets and audit remain untouched.

## Repository map

| Files | Status |
|---|---|
| `reproduce.py`, `evaluation.py`, `tests/` | Supported, rerun audit |
| `verify_fresh_download.py` | Isolated archive rebuild and exact comparison against saved evidence |
| `model_v2_temporal.py`, `model_fwl_residual.py` | Corrected standalone entry points using the shared evaluation code |
| `temporal_features.py`, `anthropometrics.py` | Shared race-history and mass features; limitations documented |
| `probe_within_athlete_nationality.py` | Legacy per-career fits reused for descriptive support counts/slopes |
| Other `model_*.py`, `probe_*.py` | Exploratory history; their printed interpretations and nominal significance are not current conclusions |
| Scrapers, enrichment, weather scripts | Historical data construction |

## Bundle integrity

`PACKAGE_MANIFEST.json` inside the ZIP records each included file’s size and SHA-256 hash. The historical notebook is included for context; the larger exploratory model collection stays in the working repository. The README and overview graphic are navigation aids; the supported numerical evidence remains in `results/audit.json` and `results/fresh_download.json`.

## Overview graphic

`docs/render_overview.py` reads those saved reports and writes `docs/overview.png` and `docs/overview.svg`. Rendering requires Matplotlib (see `docs/requirements-visual.txt`); it is optional and is not needed to run the audit. From the project directory:

```bash
python docs/render_overview.py
```
