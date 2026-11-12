# Validation — 12 November 2026

- **9 model tests passed:** all six Early forecasts and all six Pre-GDP forecasts reproduce the frozen approved Excel review to a tolerance of 1e-10. Q3 2026 Early growth reproduces 4.9307163416%.
- **7 source-integrity tests passed:** schema changes, duplicate periods, GDP reconciliation, disappearance of observed data, month-label parsing, year-boundary CPO handling and byte-for-byte preservation of the preceding snapshot on download failure.
- **Live source downloads passed:** GDP, IPI, retail volume, annual MPOB pages, official services-volume XLSX, construction dashboard and publication archives were downloaded, parsed and validated.
- **The local dashboard Update data button passed end to end:** it invoked the download service, retained the existing view while downloading, replaced the validated snapshot, and recalculated the forecast. The successful browser-tested snapshot was recorded at 14:54 MYT.
- **Browser checks passed:** desktop and 390px mobile layout, all navigation views, actual regression equations, scenario-slider recalculation, reset, historical Pre-GDP selection, unavailable-stage explanation and CSV export. Mobile page width matched its viewport without horizontal document overflow.
- **Static-hosting behaviour checked locally:** Update data displayed the GitHub workflow instructions; checking the published snapshot correctly reported no newer data; invalid repository input was rejected. No browser access token is used.
- **No browser console errors were observed** during the final desktop check.

The GitHub workflow has not been executed in the user's repository and no public deployment has occurred. Its first cloud run still needs to verify source access from a GitHub-hosted runner and the repository's Pages settings. Historical accuracy is a revised-data, previously reused six-quarter review, not a promise of future accuracy.
