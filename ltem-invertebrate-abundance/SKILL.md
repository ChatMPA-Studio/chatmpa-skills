---
name: ltem-invertebrate-abundance
version: 0.1.0
tier: 2
description: >
  Assess the abundance and diversity of key invertebrate groups at a marine
  protected area, reporting mean counts and temporal trends for four focal
  taxa (Echinoidea, Asteroidea, Holaxonia, Scleractinia) from the LTEM
  database. Fires on questions about invertebrate health at an MPA, sea
  urchin population changes, gorgonian or hard coral trends, whether
  invertebrates are recovering or declining, echinoderm abundance, or coral
  cover as measured by transect counts. Also fires when the user asks for
  invertebrate KPIs or trends at a specific site.
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
acquire:
  - source: payload
    as: data
    provider:
      server: ltem
      tool: get_invertebrate_data
      params:
        mpa:    mpa
        region: region
        reef:   reef
        year:   year
    columns:
      - time
      - reef
      - taxa
      - value
      - region
output:
  table: trend_summary
# GAM por taxón con REML: determinista. Se comparan desviance explained y
# el número de años usados por taxón.
comparable_value: [dev_expl_pct, n_years]
reference: references/cabo_pulmo_inv_reference.json
validation:
  params: {}
depends_on: []
---

# LTEM Invertebrate Abundance

## Purpose
Answers whether key invertebrate groups are increasing, stable, or declining
at a monitored reef site by fitting a separate GAM per focal taxon, producing
smooth population-level trends with 95% CI. Reports observed mean counts for
the most recent survey years as the KPI per taxon.

## Data contract (minimal interface, NOT the local file)
Input — reef-year level invertebrate abundance (one row per year × reef × taxon):
- `time` — survey year (integer)
- `reef` — reef identifier (character; used as random effect in GAM)
- `taxa` — one of: `"Echinoidea"`, `"Asteroidea"`, `"Holaxonia"`, `"Scleractinia"`
- `value` — mean abundance count per transect for that reef-year-taxon
- `region` — LTEM monitoring region name (for output labelling only)
- `richness` — mean species richness per transect (optional)

MCP source (Stage 2 of ORCHESTRATION):
- `mcp__ltem__invertebrate_temporal_trends(region = <region>)` if it exposes
  reef-level data; otherwise use the raw observations endpoint and aggregate
  to reef-year level before passing to this skill.

Focal taxa (fixed — 4 only):
- `Echinoidea` — sea urchins (`taxa2 == "Echinoidea"`)
- `Asteroidea` — sea stars (`taxa2 == "Asteroidea"`)
- `Holaxonia` — gorgonian corals (`taxa3 == "Holaxonia"`)
- `Scleractinia` — hard corals / stony corals (`taxa3 == "Scleractinia"`)
Records not matching any focal taxon are excluded.

Processing already applied by the MCP before data reaches this skill:
- Records filtered to `label == "INV"`
- Taxa classification: Holaxonia > Scleractinia (taxa3), then Asteroidea >
  Echinoidea (taxa2); non-matching records excluded
- Aggregation: transect (SUM quantity, n_distinct species) → reef-year (MEAN)
- Consistent site filter: reefs monitored ≥ 5 years only

Missing-data rule: if a reef is absent in a given year, that row is missing —
do not impute. The GAM handles irregular sampling. Require at least 5 unique
years per taxon to fit the model; if not met, return `"insufficient_data"` for
that taxon.

## Method (fixed, no degrees of freedom)

### Trend: GAM with reef random effect (fit independently per taxon)
Formula: `quantity ~ s(year, k = k_use) + s(reef, bs = "re")`
- `k_use = min(10, n_distinct_years_for_taxon - 1)` — smoothing knots, capped at 10
- `s(reef, bs = "re")` — reef as random effect; accounts for repeated measurements
  and between-reef variation within each taxon
- `family = gaussian()` — Gaussian error; consistent with reference implementation
- `method = "REML"` — Restricted Maximum Likelihood for optimal smoothing
- Lower bound of CI clipped at 0: `lwr = max(fit - 1.96 × se.fit, 0)` (counts
  cannot be negative)

Prediction: evaluate over a 200-point year grid per taxon, **excluding the reef
random effect** to obtain the population-level trend.

### KPI — observed mean abundance
Arithmetic mean of `value` across all reefs per survey year, computed for the
most recent 5 survey years per taxon, then averaged. Reported with SD.

## Random controls
None. The GAM is deterministic given REML optimization.

## Reference value and tolerance
- Reference case: **PENDING** — Cabo Pulmo, most recent year available.
  Source: `ltem_report/artifacts/figure9_echi-ast_bars_CaboPulmo.png` (Echinoidea,
  Asteroidea) and `figure10_holax-scle_bars_CaboPulmo.png` (Holaxonia, Scleractinia).
- Tolerance: PENDING.
- Status: PENDING — do NOT use as reference until verified by Edu/Fabio.
  Stored in `references/cabo_pulmo_inv_reference.json`.

## Do-not rules
- Do NOT change `k` above 10 or below `n_taxon_years - 1` — follow the reference
  implementation from `ltem_report/workshops/datamares/2026/generate_fig_invertebrates.R`.
- Do NOT use Poisson or Gamma family — the reference uses Gaussian; do not change
  without updating SKILL.md and ltem_report.
- Do NOT mix taxa in a single GAM — each taxon is fit independently.
- Do NOT aggregate across taxa — each of the 4 must appear separately in the output.
- Do NOT use the `invertebrate_temporal_trends` MCP output if it only returns
  pre-aggregated annual means (lacking the `reef` column). The GAM requires
  reef-level data for the random effect.
- Do NOT fit the GAM with fewer than 5 unique survey years per taxon.

## Validation checklist
- [ ] self-consistency: run twice on the same input → identical fit/lwr/upr per taxon.
- [ ] reference: KPI mean abundance per taxon for Cabo Pulmo matches `references/`
      value within tolerance (PENDING until reference is set).
- [ ] coherence: GAM trend directions are ecologically plausible per taxon; deviance
      explained reported in method metadata.

## Success criteria
A complete invertebrate abundance analysis includes:
- KPI: observed mean abundance per transect for each of the 4 focal taxa
  (most recent 5 years) ± SD.
- Trend: GAM smooth per taxon with 95% CI (lwr clipped at 0) + deviance explained.
- Observed annual means ± SE per taxon (for overlaying on the trend plot).
- Species richness per taxon if richness data is present in the input.
