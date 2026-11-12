# Malaysia GDP Nowcast

A GitHub Pages-ready web version of the approved five-sector Excel nowcasting model. Navy, yellow and restrained red accents use the palette published in MOF's Budget 2026 identity guide. The dashboard is a research tool; it is not an official GDP release.

## Start locally

Python 3.10+ is needed for the local data-download service. The dashboard itself is plain HTML, CSS and JavaScript, with no frontend dependencies or build step.

```sh
python -m pip install -r requirements.txt
python scripts/serve.py
```

Open **http://127.0.0.1:8767**. The yellow **Update data** button downloads all official sources, validates them and recalculates the selected nowcast. The previous snapshot remains intact if any download or validation fails. The server binds only to localhost.

On Windows, you can instead double-click **START_DASHBOARD.cmd**. It uses the installed Codex Python runtime when available, opens your browser, and keeps the local refresh service running until you close its console or press Ctrl+C. No Excel or VBA setup is required.

To refresh data from a terminal:

```sh
python scripts/update_data.py
```

To run the model-parity tests (Node.js 22+):

```sh
node --test tests/*.test.mjs
```

## Publish on GitHub Pages

1. Create a GitHub repository. Upload **this folder's contents**, including `.github/workflows`, to its `main` branch. The repository root must contain `dist`, `scripts`, `tests`, `requirements.txt` and `.github`.
2. In **Settings → Pages → Build and deployment**, set **Source: GitHub Actions**.
3. In **Actions**, select **Update data and publish dashboard → Run workflow**. Leave **Download fresh official data** checked for a live update. Uncheck it only to publish the already bundled, date-labelled snapshot.
4. Wait for the build and deployment jobs. GitHub Pages will provide your URL, usually `https://USERNAME.github.io/REPOSITORY/`.

The included workflow refreshes sources on **weekdays at 13:30 Malaysia time (05:30 UTC)**. GitHub can delay scheduled runs, particularly in inactive repositories. A failed refresh fails the build and leaves the previous successful deployment online.

The dashboard reads the repository name injected during deployment. Its **Update data** button on GitHub Pages opens a secure GitHub workflow link. Sign in to GitHub, choose **Run workflow**, then return to the dashboard and click **Check for updated data** after deployment finishes. A static page cannot dispatch authenticated GitHub workflows by itself without an authentication service. No access token is embedded, requested or stored in the browser. Local mode supports a direct one-click refresh.

No GitHub publication has been performed for you: upload this project to your chosen repository when ready. You can also host `dist` on any static web server; it must be served over HTTP rather than opened with `file://`.

## Dashboard views

- **Overview:** headline GDP, historical chart, sector forecasts, contributions and review error.
- **Sector lab:** the actual fitted coefficients, training window and growth assumptions. Sliders calculate a separate scenario; they never modify baseline forecasts or observed data.
- **Data explorer:** all active monthly indicators, quarterly indicators, GDP history, source units, download links, observation counts and publication dates. CSV downloads preserve the original numerical units.
- **Methodology:** model stages, equations, selected predictors, aggregation and the small revised-data review.

Choose a target quarter, cutoff and **Auto / Early / Pre-GDP**. Auto only enables the late model when the required monthly observations and both quarterly releases have been published by the cutoff. Target and later GDP are excluded from coefficient fitting. A forced unavailable stage produces an explanation, not a substitute number.

## Retained specification

The base equations below are retained. A frozen historical-bias policy adds **+0.20 percentage points to Pre-GDP services growth** for Q3 2026 onward, with cutoffs on or after 12 November 2026. All other factors are zero. See [ADD_FACTORS.md](ADD_FACTORS.md) for calibration, later-period checks, limitations and reproduction. Sector lab and CSV exports disclose raw growth and the fixed factor. The original six-quarter accuracy figures below describe the unadjusted historical specification.

| Component | Early (first two months) | Pre-GDP (full quarter) |
|---|---|---|
| Agriculture | Equal CPO bridge / GDP AR blend; all valid history | Same methods with all three CPO months |
| Mining | Mining IPI bridge; last 16 valid quarters | Same bridge with full-quarter IPI |
| Manufacturing | Manufacturing IPI bridge; last 16 | Same bridge with full-quarter IPI |
| Construction | Prior-quarter construction GDP YoY | Nominal work-done YoY bridge; last 16 |
| Services | Retail-volume bridge / GDP AR blend; last 12 | Services-volume YoY bridge; last 12 |
| Import duties | GDP AR(1); last 12 | Unchanged |

Every regression requires at least 12 valid preceding quarters. Sector level = prior-year level × (1 + forecast YoY). Headline growth = sum of five sector levels and duties ÷ official prior-year total GDP − 1. Official component rounding is retained. Net exports were assessed separately and are not an active predictor.

## Data sources and refresh integrity

- GDP: https://storage.dosm.gov.my/gdp/gdp_qtr_real_supply.csv
- Mining/manufacturing: https://storage.dosm.gov.my/ipi/ipi_1d.csv
- Retail volume: https://storage.dosm.gov.my/iowrt/iowrt_2d.csv
- CPO: https://bepi.mpob.gov.my/stat/web_report1.php?val=202684 (annual pages discovered through the current year)
- Services volume: official downloadable DOSM workbook, discovered from its release archive: https://www.dosm.gov.my/portal-main/release-archive/volume-index-of-services-Q22026
- Construction: https://open.dosm.gov.my/dashboard/construction-statistics
- Actual IPI, retail, services, construction and GDP publication dates: official DOSM release archives.
- Design palette: https://belanjawan.mof.gov.my/pdf/2026/garis-panduan-belanjawan-2026.pdf

Downloads are staged under ignored `data_snapshots/`. The script checks schema, duplicates, source levels, minimum history, GDP component reconciliation and loss of previously observed data. It atomically replaces `dist/data/model-data.json` only after the complete refresh passes. Source layout changes stop the operation; they do not silently substitute an indicator. No API key is required.

On GitHub, the workflow first restores the last publicly deployed snapshot as the coverage baseline. For a first deployment, a 404 response leaves the bundled baseline in place. Other restore errors stop deployment. This workflow targets publicly readable GitHub Pages; authenticated private Pages hosting needs a different baseline-retrieval method.

## Accuracy and limits

Frozen fixtures reproduce the approved Excel review: Early GDP MAE **0.363293 pp**, Pre-GDP **0.272341 pp**, over 2025Q1–2026Q2. The frozen Q3 2026 Early headline is **4.930716%**. Current refreshed data may revise these results, so the dashboard calculates its review from the current snapshot and reports how many of six quarters are available.

The review sample has been reused in earlier model work. The data are latest revised levels, not original publication vintages. A retrospective cutoff enforces recorded publication timing but cannot undo later revisions. MPOB pages do not supply a complete historical CPO release calendar. The cutoff gates verify monthly IPI/retail and quarterly releases; observed CPO is a latest-vintage input. The target quarter's regular GDP is never used to fit its forecast. Scenario outputs are user assumptions, not confidence intervals or independently fitted forecasts.

## Project map

```text
dist/                  Deploy this static directory
  model.js             Deterministic regression and aggregation engine
  app.js               Dashboard interactions, data tables and exports
  data/model-data.json Validated active source snapshot
scripts/update_data.py Public-source extraction and atomic refresh
scripts/serve.py       Local dashboard and refresh endpoint
tests/                 Frozen Excel parity and model-boundary tests
.github/workflows/     Scheduled/manual refresh and Pages deployment
```

`seed_workbook.py` is a migration utility used in the original workspace; normal use, refresh and GitHub deployment do not need the Excel file or VBA.
