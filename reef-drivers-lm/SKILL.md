---
name: reef-drivers-lm
version: 0.1.0
tier: 1
description: >
  Identify which environmental and fishing pressure factors are associated with
  reef trophic health at a marine protected area, by fitting a linear model of
  NRSI against local fishing pressure (CPUE by species and fleet), thermal
  anomaly (SST), and primary productivity anomaly (chlorophyll-a). Fires on
  questions about what drives reef condition, whether fishing or temperature has
  a stronger association with reef health, or which factors explain year-to-year
  variation in reef trophic state.
inputs:
  species:
    type: array
    required: true
    description: >
      One or more canonical scientific names (`nombre_cientifico_canonico`).
      Each species produces two CPUE predictors (MENORES and MAYORES).
      Keep to ≤ 3 species for short time series. Must be resolved before
      calling conapesca-cpue (common names not accepted).
acquire:
  - source: skill_output
    skill: ltem-nrsi-index
    as: data_nrsi
    columns: [time, reef, nrsi]
  - source: skill_output
    skill: conapesca-cpue
    as: data_cpue
    note: >
      Named list — one element per species (name = canonical scientific name),
      each a data.frame with columns anio_corte, tipo_aviso, cpue_media, escala.
      The orchestrator filters each to escala="local" before passing.
  - source: skill_output
    skill: erddap-sst-anomaly
    as: data_sst
    columns: [year, anomalia_media]
  - source: skill_output
    skill: erddap-chlorophyll
    as: data_chl
    columns: [year, anomalia_log10]
output:
  table: coefficients
# OLS cerrado — determinista. Se comparan R² y coeficientes.
comparable_value: [r_squared, r_squared_adj]
reference: references/cabo_pulmo_lm_reference.json
validation:
  params:
    species: [Lutjanus peru]
depends_on: [ltem-nrsi-index, conapesca-cpue, erddap-sst-anomaly, erddap-chlorophyll]
---

# Reef Drivers — Linear Model (first-order integration)

## Purpose
Answers which among fishing pressure, thermal conditions, and primary
productivity are most associated with reef trophic health (NRSI) at a given
AMP, using a multiple linear regression on the annual time series produced by
the per-database skills. This is an explicitly exploratory, first-order model —
associations, not causal effects.

## Species specification (required before calling this skill)

This skill requires at least one target species expressed as a canonical
scientific name (`nombre_cientifico_canonico`). The orchestrator MUST ask the
user to specify species before calling `conapesca-cpue`.

**Stage [0] — species elicitation (mandatory)**:
- If the user has not specified species: ask explicitly.
  *"Para analizar la presión pesquera necesito saber qué especies incluir.
  Por favor indícame el nombre científico canónico de cada especie
  (tal como aparece en los registros CONAPESCA)."*
- Accept one or more species. Each species produces two CPUE predictors
  (MENORES and MAYORES), so keep the list short (≤ 3 species recommended for
  short time series).
- Do NOT proceed with a generic "todas las especies" — the model would be
  uninterpretable and CPUE units would be incomparable across taxa.

## Data contract (minimal interface, NOT the local file)

This skill receives outputs from four per-database skills, already computed and
validated. The orchestrator joins them before calling this skill.

- `data_nrsi`  — `value$nrsi_by_reef` from `ltem-nrsi-index`:
  columns: `time` (int, renamed to `year`), `reef` (chr), `nrsi` (num)
  → aggregated to AMP-year by `mean(nrsi)` within this skill before fitting.

- `data_cpue`  — **named list** of `value` data.frames from `conapesca-cpue`,
  one element per target species, filtered to `escala = "local"`:

  ```r
  data_cpue <- list(
    "Lutjanus peru"           = <conapesca-cpue output for species 1>,
    "Epinephelus labriformis" = <conapesca-cpue output for species 2>
  )
  ```

  Each element has columns: `anio_corte` (int), `tipo_aviso` (chr, "MAYORES"
  or "MENORES"), `cpue_media` (num).

  Within this skill, each species × fleet combination becomes a **separate
  predictor** column named `cpue_{fleet}_{species}`, where fleet is `menores`
  or `mayores` (lower-case) and species is the scientific name with spaces
  replaced by underscores (e.g. `cpue_menores_Lutjanus_peru`).

  MAYORES and MENORES are never averaged together — they represent different
  fishing sectors with different effort units.

- `data_sst`   — `value` from `erddap-sst-anomaly`, filtered to `escala = "local"`:
  columns: `year` (int), `anomalia_media` (num)

- `data_chl`   — `value` from `erddap-chlorophyll`, filtered to `escala = "local"`:
  columns: `year` (int), `anomalia_log10` (num)

- Missing-data rule: join on `year` using **complete cases only** — years where
  any predictor or the response is `NA` are excluded. `n_years_used` is reported
  in the output; years dropped are listed in `years_excluded`.
- Aggregation unit: **AMP-year** (one row per year). Fixed, not optional.

## Method (fixed, no degrees of freedom)

1. Aggregate NRSI to AMP-year:
   - `nrsi_mean` = `mean(nrsi)` across all reefs within the AMP per year.

2. Build CPUE predictor columns:
   - For each species `sp` in `names(data_cpue)`:
     - `sp_col` = `sp` with spaces replaced by `_` (e.g. `Lutjanus_peru`)
     - Pivot `tipo_aviso` to wide: one column `cpue_menores_{sp_col}` and one
       column `cpue_mayores_{sp_col}` per year.
     - If a fleet type is absent for a species, the column is `NA` for all
       years (will be dropped from complete cases — reported in `years_excluded`
       context).

3. Inner join all predictors on `year` → complete-case analysis.

4. Build OLS formula dynamically from available CPUE columns:
   ```
   nrsi_mean ~ cpue_menores_{sp1} + cpue_mayores_{sp1} +
               cpue_menores_{sp2} + cpue_mayores_{sp2} +
               ... + anom_sst + anom_chl
   ```
   Using base R `lm()`. No transformations, no interactions, no variable
   selection — all predictors enter the model unconditionally.

5. Check minimum sample size:
   - `n_params` = number of CPUE columns + 2 (SST, Chl) + 1 (intercept)
   - Error if `n_years_used < n_params + 1` — underdetermined system.
   - Warning if `n_years_used < 10` — low power.

6. Extract and return:
   - Coefficients, standard errors, t-values, p-values (from `summary(lm)`)
   - R² and adjusted R²
   - Model fitted values and residuals per year
   - Variance Inflation Factors (VIF) via `car::vif()` — collinearity diagnostic
   - `formula_used` (as character string, so the output is self-describing)
   - `species` (character vector, the names of `data_cpue`)

## Random controls
Not applicable — deterministic skill (OLS is closed-form, no bootstrap or
resampling in this version).

## Reference value and tolerance
- Reference case: **PENDING** — R² and coefficients for Cabo Pulmo using the
  full available time series, to be verified by Edu/Fabio against a direct
  analysis in R.
- Tolerance: PENDING (expected ± 0.01 for R², ± 0.05 for coefficients given
  deterministic OLS).
- Status: PENDING. Do NOT invent a reference value. Stored in
  `references/cabo_pulmo_lm_reference.json` with `status: PENDING`.

## Do-not rules
- Do NOT call this skill without species — require the user to provide canonical
  scientific names first.
- Do NOT average MAYORES and MENORES CPUE together — they are separate
  predictors in every case.
- Do NOT interpret regression coefficients as causal effects — this is an
  observational time series model. Report associations only.
- Do NOT run variable selection (stepwise, AIC, lasso) — all predictors enter
  unconditionally. This is a design choice to avoid overfitting on short time
  series.
- Do NOT fit the model if `n_years_used < n_params + 1` — return an error.
- Do NOT mix local and regional scale predictors in the same model — use only
  local scale for all predictors. Regional scale is for context, not regression.
- Do NOT report the model as "significant" based on p-values alone — always
  report R², n_years_used, and VIF alongside p-values.
- Do NOT silently drop years with NA — list them explicitly in `years_excluded`.
- Do NOT accept a species argument that is not a canonical scientific name
  (i.e. common names like "pargo" are not valid — ask the user to confirm the
  scientific name).

## Validation checklist
- [ ] self-consistency: run N times on fixed data, outputs match exactly
      (deterministic — tolerance = 0).
- [ ] reference: output matches `references/cabo_pulmo_lm_reference.json`
      within tolerance. PENDING → SKIP with disclosure until verified.
- [ ] coherence: output declares `method`, `params`, and `formula_used`
      matching this contract.

## Success criteria
A complete reef-drivers analysis includes:
- `formula_used` reported explicitly (so reader can see which species and fleets
  entered the model).
- `species` vector listing the scientific names used.
- Coefficient table with estimates, SE, t, p for all predictors and intercept.
- R² and adjusted R² reported explicitly.
- VIF for each predictor (flag if VIF > 5 — collinearity concern).
- `n_years_used` and `years_excluded` reported.
- Explicit statement that associations are not causal.
- Direction interpretation: sign and magnitude of each coefficient described
  in ecological terms (e.g. "each unit increase in CPUE for *Lutjanus peru*
  MENORES is associated with a decrease of X in NRSI").
