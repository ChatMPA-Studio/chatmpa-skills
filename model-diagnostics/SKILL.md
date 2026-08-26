---
name: model-diagnostics
version: 0.1.0
tier: 1
description: >
  Compute and summarise standard regression diagnostics for a fitted
  reef-drivers-lm model. Fires when the user asks whether the model assumptions
  hold, whether residuals are autocorrelated, or whether they need to interpret
  the validity of the regression before reporting results.
inputs:
  sections:
    type: array
    required: false
    default: "[normality, durbin_watson, acf_residuals, pacf_residuals, heteroscedasticity]"
    description: >
      Subset of diagnostic sections to compute. Default: all sections.
acquire:
  - source: skill_output
    skill: reef-drivers-lm
    as: lm_output
    fields: [fitted, n_years_used, formula_used, species]
output:
  table: acf_residuals
# Determinista — derivado algebraicamente de residuales y valores ajustados.
# Se comparan DW y autocorrelación de orden 1.
comparable_value: [dw, r1]
reference: references/cabo_pulmo_diag_reference.json
validation:
  params: {}
depends_on: [reef-drivers-lm]
---

# Model Diagnostics — OLS regression diagnostics for annual time series

## Purpose

Evaluates the key assumptions of the OLS linear model fitted by
`reef-drivers-lm`: independence of residuals, normality of residuals, and
homoscedasticity. All results are reported as evidence for the user to
interpret — this skill does not conclude whether the model is adequate.

## Data contract (minimal interface, NOT the local file)

Input is the complete list returned by `reef-drivers-lm`:

- `lm_output$value$fitted` — data.frame with columns:
  `year` (int), `nrsi_obs` (num), `nrsi_fit` (num), `residual` (num)
- `lm_output$value$n_years_used` — integer
- `lm_output$value$formula_used` — character string
- `lm_output$value$species` — character vector

No raw data, no `lm` object — diagnostics are computed from pre-extracted
residuals and fitted values only.

## Method (fixed, no degrees of freedom)

### normality
Shapiro-Wilk test on residuals (`shapiro.test()`).
Requires n ≥ 3. Informative only — temporal autocorrelation in residuals
inflates the W statistic, so do not use as a hard gate.

### durbin_watson
Durbin-Watson statistic computed directly from residuals:
`DW = sum(diff(e)^2) / sum(e^2)`
where `e` is the vector of residuals in chronological order.
Also reports `r1` = lag-1 autocorrelation of residuals
(`cor(e[-n], e[-1])`; note: DW ≈ 2*(1 − r1)).
Interpretation: DW ≈ 2 → no autocorrelation; DW < 1.5 → positive
autocorrelation concern; DW > 2.5 → negative autocorrelation concern.
Thresholds are heuristic — formal critical values depend on n and k
(not computed here).

### acf_residuals
ACF of residuals via `stats::acf()`, lag.max = 3.
Reports: lag, acf value, 95% CI threshold (±1.96/√n).

### pacf_residuals
PACF of residuals via `stats::pacf()`, lag.max = 3.
Reports: lag, pacf value, 95% CI threshold (±1.96/√n).

### heteroscedasticity
Score test for heteroscedasticity based on a regression of squared residuals
on fitted values: `e² ~ ŷ`.
LM statistic = n × R² from that auxiliary regression.
Under H₀ (constant variance), LM ~ χ²(1). P-value computed with `pchisq()`.
Note: this is a simplified White-type test. It does not require the original
predictors — only fitted values and residuals.

## Random controls
Not applicable — deterministic skill.

## Reference value and tolerance
- Status: PENDING. Stored in `references/cabo_pulmo_diag_reference.json`.

## Do-not rules
- Do NOT conclude that the model is "valid" or "invalid" — report the
  diagnostic statistics and let the user interpret them in context.
- Do NOT treat the Shapiro-Wilk result as a gate — report it as informative.
- Do NOT require the `lm` object or the original data — all diagnostics must
  derive from `lm_output$value$fitted` and `lm_output$value$n_years_used`.
- Do NOT interpret autocorrelated residuals as proof of model misspecification
  — they may also reflect unmeasured drivers or genuine ecological memory.

## Validation checklist
- [ ] self-consistency: outputs match exactly on repeated runs (deterministic).
- [ ] reference: PENDING → SKIP with disclosure.
- [ ] coherence: `params$formula_used` matches `lm_output$value$formula_used`.

## Success criteria
A complete diagnostics run includes all five sections:
- `normality`: W, p_value, note.
- `durbin_watson`: dw, r1, interpretation note.
- `acf_residuals`: data.frame with lag, acf, ci.
- `pacf_residuals`: data.frame with lag, pacf, ci.
- `heteroscedasticity`: lm_stat, p_value, note.
