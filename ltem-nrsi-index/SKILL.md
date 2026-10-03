---
name: ltem-nrsi-index
version: 0.1.1
tier: 2
description: >
  Assess the trophic health of a reef and answer whether it is healthy,
  degraded, or recovering, from the LTEM database. Fires on questions about
  reef trophic balance, apex-predator recovery, overfishing signatures, or
  "is this reef healthy" — by computing the Normalized Reef State Index (NRSI)
  from the relative biomass of upper, lower, and consumer trophic levels.
inputs:
  mpa:
    type: string
    required: false
    description: >
      Nombre del AMP tal como aparece en la BD LTEM (ej. "Cabo Pulmo").
      Filtra solo arrecifes dentro del polígono del parque.
      No usar junto con region: el filtro es AND y el resultado sería más
      restrictivo que cualquiera de los dos solos.
  region:
    type: string
    required: false
    description: >
      Región LTEM (ej. "Cabo Pulmo"). Incluye arrecifes dentro Y fuera del AMP.
      No usar junto con mpa: el filtro es AND y el resultado sería más
      restrictivo que cualquiera de los dos solos.
  reef:
    type: string
    required: false
    description: >
      Nombre de un arrecife específico. Usar solo si la pregunta es
      a nivel de arrecife concreto.
  year:
    type: integer
    required: false
    description: >
      Año de muestreo. Omitir para serie temporal completa.
  n_boot:
    type: integer
    required: false
    default: 100
    description: >
      Bootstrap resamples for 95% CI computation. Range 100–500. Seed is
      fixed at 42 — CIs are reproducible regardless of n_boot value.
acquire:
  - source: payload
    as: data
    provider:
      server: ltem
      tool: get_nrsi_data
      params:
        mpa:    mpa
        region: region
        reef:   reef
        year:   year
    columns:
      - time
      - value
      - TrophicLevelF
      - transect
      - reef
output:
  table: nrsi_by_reef
  columns: [time, reef, nrsi, ci_lo_95, ci_hi_95, ci_includes_zero, health_category, n_transects, n_ltl_dominant]
# Bootstrap con seed=42 — determinista. Se comparan NRSI y CIs por reef-year.
comparable_value: [nrsi, ci_lo_95, ci_hi_95]
reference: references/cabo_pulmo_nrsi_reference.json
validation:
  params:
    region: Cabo Pulmo
    n_boot: 100
depends_on: []
---

# LTEM Normalized Reef State Index (NRSI)

## Purpose
Answers whether a reef is trophically healthy, degraded, or recovering by
computing the Normalized Reef State Index (NRSI) — the relative biomass balance
of upper, lower, and consumer trophic levels — per reef, with uncertainty and
regional comparison.

## Data contract (minimal interface, NOT the local file)
- Input: a table on the minimal contract carrying, per observation:
  - `time` — survey year,
  - `value` — `Biomass` in T/ha, and
  - the categorical trophic-level range `TrophicLevelF` (e.g. `2-2.5`, `4-4.5`)
  - a transect identifier and a reef identifier for aggregation.
  `lat`/`lon` apply when NRSI is mapped spatially. The skill reads this
  interface, not a file with a fixed name.
- Trophic mapping (fixed):
  - `2-2.5` → LTL (Lower Trophic Level: herbivores, detritivores)
  - `4-4.5` → UTL (Upper Trophic Level: apex predators)
  - all other levels (`2.5-3`, `3-3.5`, `3.5-4`) → CTL (Consumer Trophic Level)
- Missing-data rule: transects where UTL=LTL=CTL=0 (no fish recorded) are
  **excluded** from the reef average with a warning. Never emit a silent NaN.
  Implemented in `skill.R`: rows with `total_biomass == 0` are dropped before
  NRSI computation; count reported as `n_empty` in the warning message.
- Aggregation unit: **transect** for NRSI computation, then averaged to
  **reef-year**. Fixed, not optional.
- Not applied: the filter of reefs monitored ≥ 5 years. `ltem_report` applies it
  in its own analysis (`04-full_trends_analysis.R:500`), so its values are not
  directly comparable with this skill's (ltem-db-mcp#10).
- Data source: Centro para la Biodiversidad Marina y la Conservación [CBMC] (2026),
  LTEM database.

## Method (fixed, no degrees of freedom)
The index follows Favoretto et al. (2024). Relative biomass proportions UTL, LTL, CTL are computed **within each transect**
(each category's summed biomass / total), then:

```
Standard:     NRSI = (UTL + LTL - CTL) / (UTL + LTL + CTL)
Conditional:  if LTL > UTL + CTL,  NRSI = UTL / (UTL + CTL)
```

The conditional prevents artificially high NRSI when herbivore/detritivore
biomass (LTL) dominates the system. NRSI is computed per transect, then averaged
per reef.

Computation steps: classify each observation's `TrophicLevelF` → sum biomass per
transect per category → compute relative proportions → apply standard or
conditional formula per transect → average transect NRSI per reef.

- Reference: NRSI formula from Favoretto et al. (2024), including the conditional
  rule (present in the paper's code, `CBMC-GCMP/nrsi`, `01-analysis.R`). The
  implementation follows the LTEM analysis script (`04-full_trends_analysis.R`,
  section `# NRSI`, lines 499–640 in version a9ac148, 2025-11-25); bootstrap adapted
  from `resample_mean()` in the same script. See `references/nrsi_methodology.md`.
- Parameters (documented defaults): bootstrap `n_boot = 100` (range 100–500);
  95% CI from the 2.5th and 97.5th percentiles of the bootstrap distribution
  (percentile bootstrap; Efron & Tibshirani, 1993). Favoretto et al. (2024) use
  9,999 resamples; this skill keeps 100 by default.

### Interpretation
Computed on the annual NRSI series (mean across reefs per year):
- Before/after comparison (`before_after()`): first 5 years vs. last 5 years.
- Mann-Kendall test (Mann, 1945; Kendall, 1975) via `mk_trend()`
  (`Kendall::MannKendall`, `shared/interpretation/interpret.R`); minimum number of
  years as set in `mk_trend()`.
- Status: `"positive"` if `after_mean > 0` and the direction is increasing;
  `"negative"` if `after_mean < −0.15`, or if `delta < −0.1` and Mann-Kendall
  p < 0.10; otherwise `"neutral"`.

## Random controls
- Seed: **fixed at `42`** (`set.seed(42L)` called once before the bootstrap
  loop in `skill.R`). CIs are fully reproducible across runs.
- Bootstrap: resample transect-level NRSI values within each reef, with
  replacement (n = number of transects per reef), `n_boot = 100` by default.
- The seed is set once for the whole run: the CIs depend on the order of the
  reef × year groups and on the full dataset, so the reference case runs on the
  whole region without filtering year or reef.

## Reference value and tolerance
- Reference cases: 3 (`nrsi`, `ci_lo_95`, `ci_hi_95`) in
  `references/cabo_pulmo_nrsi_reference.json`.
- Case: Cabo Pulmo region, full series, `n_boot` = 100, seed = 42; the row compared
  is year 2023, reef LOBERA_CABO_PULMO (8 transects).
- Expected values: `nrsi` = −0.1891, `ci_lo_95` = −0.5274, `ci_hi_95` = 0.1506,
  verified by Carolina (2026-10-02) with an independent calculation on LTEM server
  data (`get_nrsi_data`, snapshot 2026-10-02).
- Tolerance: ±0.00005 (the skill rounds to 4 decimals).
- Seed: 42.
- Status: VERIFIED.

## Do-not rules
- Do NOT emit a silent NaN for the UTL=LTL=CTL=0 edge case (transect with no
  fish). Exclude from the reef average with a warning — implemented in `skill.R`.
- Do NOT run the bootstrap without a fixed seed — CIs would not be reproducible
  across runs. Seed is fixed at `42` in `skill.R`.
- Do NOT report NRSI as a confident assessment when the bootstrap 95% CI
  includes 0 — the reef's trophic state is ambiguous; say so.
- Do NOT let LTL dominance inflate NRSI — apply the conditional rule, do not
  use the standard formula when LTL > UTL + CTL.

## Validation checklist
- [ ] self-consistency: run N times on fixed data, outputs match within tolerance.
- [ ] reference: output matches the references/ value within tolerance.
- [ ] coherence: the output uses the methods this contract specifies.

### Resolved fixes (implemented in `skill.R`)
- [x] Seed fixed at `42` (`set.seed(42L)`) — bootstrap CIs are reproducible.
- [x] UTL=LTL=CTL=0 edge case: transects with zero total biomass are excluded
      with a `warning()` before NRSI computation; count reported in message.
- [x] Reference cases created and verified: `references/cabo_pulmo_nrsi_reference.json`
      (`status: VERIFIED`).

## Success criteria
A complete NRSI analysis includes:
- Regional comparison with a statistical test (Kruskal-Wallis across regions).
- Per-reef NRSI for at least one region, with highest/lowest reefs identified.
- Bootstrap 95% confidence intervals for key reefs (flag CIs that include 0).
- Temporal comparison if multiple years are available.
- A clear mapping of NRSI values to ecological health categories:
  0.5–1.0 Excellent · 0.0–0.5 Good · -0.5–0.0 Degraded · -1.0–-0.5 Severely degraded.

## References
- Centro para la Biodiversidad Marina y la Conservación. (2026). *Programa de
  Monitoreo Ecológico de Largo Plazo (LTEM)* [Datos sin publicar].
- Efron, B., & Tibshirani, R. J. (1993). *An introduction to the bootstrap*.
  Chapman & Hall. https://doi.org/10.1007/978-1-4899-4541-9
- Favoretto, F., López-Sagástegui, C., León-Solórzano, E., & Aburto-Oropeza, O.
  (2024). A scalable and normalized reef status index for assessing fish trophic
  structure reveals conservation gaps. *Ecological Indicators, 166*, Article 112515.
  https://doi.org/10.1016/j.ecolind.2024.112515
- Kendall, M. G. (1975). *Rank correlation methods* (4th ed.). Charles Griffin.
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica, 13*(3),
  245–259. https://doi.org/10.2307/1907187
- McLeod, A. I. (2025). *Kendall: Kendall rank correlation and Mann-Kendall trend test*
  (Version 2.2.2) [R package]. https://CRAN.R-project.org/package=Kendall
