# Historical sector add-factor review — 12 November 2026

The purpose is to correct recurring forecast bias, not reproduce the Q3 2026 DOSM advance estimate. Positive factors raise sector YoY growth in percentage points; GDP is then re-aggregated using prior-year levels.

## Frozen policy

| Component | Early factor (pp) | Pre-GDP factor (pp) |
|---|---:|---:|
| Agriculture | 0 | 0 |
| Mining & quarrying | 0 | 0 |
| Manufacturing | 0 | 0 |
| Construction | 0 | 0 |
| Services | 0 | +0.20 |
| Import duties | 0 | 0 |

Applies to Q3 2026 and later, only for information cutoffs on or after 12 November 2026. It persists across refreshes; coefficients continue to fit normally but the add factor is never automatically re-estimated. Earlier forecasts retain their original values. Auto uses the policy for its selected stage. Sector lab and forecast CSV expose the raw forecast and applied factor. Scenario sliders operate on the adjusted baseline.

## Evidence and selection

Re-created historical forecasts at the day before each quarter's preliminary GDP release, enforcing the existing release gates and excluding target GDP from fitting. Available coverage is 14 quarters, 2023Q1–2026Q2. Data are latest revised observations, not archived real-time vintages. Early uses two months even at the later cutoff; this does not reproduce every original advance-release information set.

Magnitude estimation uses 2023Q1–2024Q4 (8 quarters). Candidate = mean(actual sector growth − model growth), rounded to 0.1 pp. Check period is 2025Q1–2026Q2 (6 quarters), which has already been reused in previous model development. It is a chronological check, not an independent final test or proof of permanent bias. All errors are in percentage points.

Pre-GDP services: calibration mean shortfall +0.2318 pp, with positive errors in 7 of 8 quarters. Rounded factor +0.20 pp reduces check-period sector MAE from 0.2188 to 0.1673 pp. Headline MAE declines from 0.2723 to 0.2328 pp (about 14.5%).

Early services: calibration mean shortfall +0.4227 pp. Although +0.40 pp slightly helps sector errors, headline MAE worsens from 0.3633 to 0.3756 pp. Retain zero.

Agriculture, mining and manufacturing: mean error changes sign between calibration and check periods; fixed factors fail the later-period error check. Retain zero even though Q3's agriculture and manufacturing forecasts differ from the advance estimate.

Construction: Early bias changes direction. Pre-GDP +0.30 pp improves the later-period errors, but calibration errors have the same sign in only 5 of 8 quarters; the later bias is much larger. Evidence is weaker than services and insufficient for a fixed permanent correction. Retain zero pending more quarters.

Import duties: calibration mean shortfall +1.4147 pp, but positive errors occur in only 4 of 8 quarters. Check-period mean shortfall jumps to +9.6853 pp. A +1.40 pp candidate helps later errors, but the unstable magnitude does not establish a stable fixed bias. Retain zero; investigate the duties model separately instead of adopting the later-period mean as a permanent factor.

The policy was selected using this check period. Future quarters must be reviewed prospectively. Q3 2026's 5.3% advance result was not used to calculate the factor. Fixed means do not guarantee improved future forecasts; continued deterioration would warrant an explicit policy revision.

## Reproduction and checks

Run `node scripts/review_add_factors.mjs` for all sector errors, training means, candidate factors and later-period MAE/RMSE. `ADD_FACTOR_REVIEW.json` stores the analysis snapshot. A future data refresh may revise the retrospective diagnostics but does not alter the constants in `dist/model.js`.

Run `node --test tests/model.test.mjs`. The tests preserve original Excel parity and verify the stage/date boundaries, exact services adjustment, weighted GDP effect and component reconciliation.
