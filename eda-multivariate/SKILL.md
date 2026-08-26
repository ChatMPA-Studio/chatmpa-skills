---
name: eda-multivariate
version: 0.1.0
tier: 1
description: >
  Explore the structure of a multivariate annual time series before committing
  to a specific analysis. Computes summary statistics, normality checks,
  temporal trends, pairwise correlations, and outlier detection across all
  variables simultaneously. Fires on questions about data structure, whether
  variables are correlated, whether there are temporal trends worth noting,
  or when the user wants to understand the data before choosing an analysis.
inputs:
  sections:
    type: array
    required: false
    default: "[summary, normality, trends, correlations, outliers, crosscorr]"
    description: >
      Subset of EDA sections to compute. Valid values: summary, normality,
      trends, correlations, outliers, crosscorr. Default: all sections.
acquire:
  # El orquestador alinea los outputs de las per-database skills por año y
  # manda la tabla en el body. Columna `year` obligatoria; el resto son variables.
  - source: payload
    as: data
    columns:
      - year  # más una columna por variable; nombres definidos por el orquestador
output:
  table: trends
# Determinista. Se comparan tau y dirección del Mann-Kendall por variable.
comparable_value: [tau, p_value_hr, direction]
reference: references/cabo_pulmo_eda_reference.json
validation:
  params: {}
depends_on: []
---

# EDA Multivariado — Exploratory Data Analysis for annual ecological time series

## Purpose

Characterizes the joint structure of a set of annual ecological time series
before any modelling decision is made. All variables are treated equally —
this skill does not assume which are predictors and which are responses. That
decision belongs to the user and to downstream analysis skills.

## Data contract (minimal interface, NOT the local file)

Input is the `aligned` table from `temporal_align()`:

- One row per year, one column per variable, plus a `year` column.
- All non-`year` columns are treated as variables to analyze.
- Rows where ALL variables are `NA` are dropped before any computation.
- `NA` values within a variable are handled per-section (reported in `n_valid`
  for summary; excluded pairwise for correlations; excluded per-variable for
  trends and normality).

Additional argument:
- `sections` — character vector controlling which sections appear in the output.
  Default: all sections. Options: `"summary"`, `"normality"`, `"trends"`,
  `"correlations"`, `"outliers"`. Passing a subset computes ONLY those sections.

## Method (fixed, no degrees of freedom)

All sections are computed on the raw values as delivered by `temporal_align`.
No transformations are applied inside this skill.

### summary
Per variable: `n_valid`, `mean`, `median`, `sd`, `min`, `max`, `skewness`.
Skewness = m3 / m2^(3/2) where m_k = mean((x - mean(x))^k) — moment estimator,
no bias correction.

### normality
Shapiro-Wilk test per variable (`shapiro.test()`, base R).
Requires n_valid ≥ 3 and ≤ 5000. Reports W statistic and p-value.
Result is **informative only** — do not use to gate downstream analyses.
Note in output: "Shapiro-Wilk assumes i.i.d. observations; temporal
autocorrelation may inflate W."

### trends
Mann-Kendall test with Hamed & Rao (1998) autocorrelation correction,
via `modifiedmk::mmkh()`.
Reports: tau, corrected p-value (`p_value_hr`), original p-value
(`p_value_mk`), trend direction (`"increasing"`, `"decreasing"`, `"none"`
at α = 0.05 on the corrected p-value).
Note in output: "Hamed & Rao (1998) correction applied for serial
autocorrelation. Requires n_valid ≥ 4."

**Reference:** Hamed K.H. & Rao A.R. (1998). A modified Mann-Kendall trend
test for autocorrelated data. *Journal of Hydrology*, 204, 182–196.

### correlations
Spearman rank correlation matrix across all variable pairs.
Uses pairwise complete observations.
Reports: correlation matrix (`rho`) and p-value matrix (`p_value`),
computed with `cor.test(..., method = "spearman")` for each pair.
Spearman is used (rather than Pearson) because ecological variables
are frequently non-normal and relationships may be monotonic but
non-linear.

### outliers
Per variable: years where the value exceeds ± 2 SD from the variable mean.
Reports the flagged years and their values. The 2 SD threshold is fixed.
These are flags for inspection, not grounds for exclusion.

### crosscorr
Cross-correlation function (CCF) between all variable pairs, at lags 0, ±1,
±2, ±3 years. Computed with `stats::ccf()` on pairwise complete observations.
Reports: lag, cross-correlation coefficient, and the 95% CI threshold
(±1.96/√n, where n = number of pairwise complete years).
Requires n ≥ 6 pairwise complete observations.
Convention: negative lag means the first variable (left of "~") leads the second.
Use to inform lag selection before fitting `reef-drivers-lm` or any other model.

## Random controls
Not applicable — deterministic skill (no bootstrap or resampling).

## Reference value and tolerance
- Reference case: PENDING — summary statistics and Spearman correlation
  between NRSI and SST anomaly for Cabo Pulmo, full available series,
  to be verified by Edu/Fabio.
- Tolerance: PENDING.
- Status: PENDING. Stored in `references/cabo_pulmo_eda_reference.json`.

## Do-not rules
- Do NOT apply transformations to the data inside this skill — analyze
  variables as received. If a log transform is warranted, the caller
  applies it before passing data.
- Do NOT treat normality results as a hard gate — they are informative context.
- Do NOT interpret correlations as causal — report Spearman rho and let the
  user decide.
- Do NOT exclude outlier-flagged years from the aligned table — flag them in
  the output only.
- Do NOT assume which variables are predictors or responses — treat all equally.

## Validation checklist
- [ ] self-consistency: run N times on fixed data, outputs match exactly
      (deterministic — tolerance = 0).
- [ ] reference: output matches `references/cabo_pulmo_eda_reference.json`
      within tolerance. PENDING → SKIP with disclosure.
- [ ] coherence: output declares `method` and `sections_computed` matching
      this contract.

## Success criteria
A complete EDA includes, for each requested section:
- `summary`: table with one row per variable, all 7 statistics.
- `normality`: table with W and p-value per variable, plus the informative note.
- `trends`: table with tau, p_value_hr, p_value_mk, direction per variable,
  plus the Hamed & Rao note.
- `correlations`: rho matrix and p-value matrix, both n_vars × n_vars.
- `outliers`: named list, one element per variable, listing flagged years.
- `crosscorr`: named list, one element per variable pair ("var1 ~ var2"), each
  a data.frame with columns `lag`, `ccf`, `ci`, `note`.
- `sections_computed` declared in output metadata.
