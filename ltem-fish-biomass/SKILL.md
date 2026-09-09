---
name: ltem-fish-biomass
version: 0.1.0
tier: 2
description: >
  Assess fish standing stock and recovery trends at a marine protected area,
  reporting mean fish biomass (g/m²) and its temporal trend from the LTEM
  database. Fires on questions about fish biomass recovery at an MPA, whether
  fish stocks are increasing or declining, the current fish standing stock,
  how biomass has changed over time, or whether protection has led to biomass
  recovery. Also fires when the user asks for the fish biomass KPI or trend
  at a specific site.
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
  # El orquestador consulta el MCP de LTEM a nivel reef-year (con reef_id)
  # y manda la tabla en el body. No usar annual_time_series — pierde el reef.
  - source: payload
    as: data
    provider:
      server: ltem
      tool: get_biomass_data
      params:
        mpa:    mpa
        region: region
        reef:   reef
        year:   year
    columns:
      - time
      - reef
      - value
      - region
  - source: payload
    as: data_behavioral
    required: false
    provider:
      server: ltem
      tool: behavioral_group_biomass
      params:
        mpa:    mpa
        region: region
        reef:   reef
        year:   year
    columns:
      - year
      - functional_name
      - mean_biomass
      - n_transects
  - source: payload
    as: data_family
    required: false
    # Devuelve TODAS las familias — el filtro por familia (ej. Serranidae,
    # Lutjanidae, Carangidae) es responsabilidad del caller (chat-mpa),
    # igual que el top-N en data_species. No se expone families como input
    # del skill porque el filtro es una decisión de presentación aguas abajo.
    provider:
      server: ltem
      tool: family_biomass
      params:
        mpa:    mpa
        region: region
        reef:   reef
        year:   year
    columns:
      - year
      - family
      - mean_biomass
      - n_transects
  - source: payload
    as: data_species
    required: false
    provider:
      server: ltem
      tool: species_biomass
      params:
        mpa:    mpa
        region: region
        reef:   reef
        year:   year
    columns:
      - species_id
      - species_name
      - trophic_group
      - mean_biomass
      - n_transects
output:
  table: annual_means
  columns: [year, mean_biomass_t_ha, se_t_ha, n_reefs]
# GAM con REML: determinista dado el ajuste. El KPI es media aritmética.
comparable_value: [mean_biomass_t_ha, se_t_ha]
reference: references/cabo_pulmo_biomass_reference.json
validation:
  params: {}
depends_on: []
---

# LTEM Fish Biomass

## Purpose
Answers whether fish biomass is recovering, stable, or declining at a monitored
reef site by fitting a GAM to the annual reef-level biomass series, producing a
smooth population-level trend with 95% CI. Reports the observed mean for the most
recent survey years as the KPI.

## Data contract (minimal interface, NOT the local file)
Input — reef-year level biomass (one row per year × reef combination):
- `time` — survey year (integer)
- `reef` — reef identifier (character; used as random effect in GAM)
- `value` — mean fish biomass (g/m²) for that reef-year (averaged across transects).
  skill.R converts to T/ha (× 0.01) before any computation.
- `region` — LTEM monitoring region name (used for output labelling only)
- `n_transects` — number of transects contributing (optional; for diagnostic reporting)

Optional secondary input — behavioral functional group biomass (`data_behavioral`),
one row per year × functional_name. Feeds `TrophicYear` schema.
- `year` — survey year
- `functional_name` — one of 6 behavioral categories:
  `GenPred_solitary` (Depredadores solitarios),
  `GenPred_schooling` (Depredadores en cardúmenes),
  `EpiBent_schooling` (Omnívoros en cardumen),
  `Crip_schooling` (Herbívoros en cardumen),
  `Crip_solitary` (Crípticos solitarios),
  `Plank` (Planctívoros).
  Species with `functional_name = 'Pelagic'` or without a match in `species_traits`
  are excluded by the MCP. Maps 1:1 to the 6 fields of `TrophicYear`.
- `mean_biomass` — mean biomass (g/m²); SUM per transect → AVG per reef → AVG per year.
- `n_transects` — total transects contributing across reefs.

Optional input — biomass by taxonomic family (`data_family`), one row per year × family.
Feeds `GET /species/family-biomass`. Unit: g/m² (consistent with `get_biomass_data`).
The tool returns ALL families — filtering to specific families (e.g. Serranidae, Lutjanidae,
Carangidae) is the caller's responsibility, analogous to how top-N selection is delegated
to the caller for `data_species`.
- `year` — survey year
- `family` — taxonomic family
- `mean_biomass` — mean biomass (g/m²); SUM per transect then AVG across transects
- `n_transects` — number of transects contributing

Optional input — biomass by species (`data_species`), one row per species.
Feeds `GET /biomass/top-species`. Unit: g/m² (consistent with `get_biomass_data`).
Biomass is collapsed across years unless `year` is specified. Ranking (top-N) is the
caller's responsibility.
- `species_id` — IDSpecies from ltem_historical_database
- `species_name` — scientific name
- `trophic_group` — TrophicGroup from ltem_historical_database
- `mean_biomass` — mean biomass (g/m²); SUM per transect then AVG across transects
- `n_transects` — number of transects contributing

MCP source (Stage 2 of ORCHESTRATION):
- Primary: `mcp__ltem__get_biomass_data(mpa, region, reef, year)` — reef-year biomass
  (year × reef, transect aggregation already done). NOT `annual_time_series`
  (already aggregated — lacks reef column needed for random effect).
- Optional breakdown by behavioral functional group: `mcp__ltem__behavioral_group_biomass(mpa, region, reef, year)` — feeds `TrophicYear`
- Optional breakdown by taxonomic family: `mcp__ltem__family_biomass(mpa, region, reef, year)` — feeds `GET /species/family-biomass`
- Optional breakdown by species: `mcp__ltem__species_biomass(mpa, region, reef, year)` — feeds `GET /biomass/top-species`

Processing already applied by the MCP before data reaches this skill:
- Fish records filtered to `label == "PEC"` and `Biomass IS NOT NULL`
- Outlier removal: `size_check()` at 95th quantile
- Corredor region: Haemulidae and Carangidae records with `biomass > 3` excluded
- Aggregation: within-reef mean across transects for each year
- Consistent site filter: only reefs monitored ≥ 5 years retained
- Unit: g/m² (note: 1 g/m² = 0.01 T/ha for conversion if needed)

Missing-data rule: if a reef-year combination is missing (reef not surveyed in
a given year), that row is absent — do not impute. The GAM handles irregular
sampling via the smooth. Require at least 5 unique years across all reefs to
fit the model; otherwise return `"insufficient_data"`.

## Method (fixed, no degrees of freedom)

### Trend: GAM with reef random effect
Formula: `biomass ~ s(year, k = k_use) + s(reef, bs = "re")`
- `k_use = min(10, n_distinct_years - 1)` — smoothing knots, capped at 10
- `s(reef, bs = "re")` — reef as random effect; accounts for pseudo-replication
  (same reef surveyed across multiple years) and between-reef variation
- `family = gaussian()` — Gaussian error; consistent with reference implementation
- `method = "REML"` — Restricted Maximum Likelihood for optimal smoothing selection

Prediction: evaluate over a 200-point year grid, **excluding the reef random
effect** (`exclude = "s(reef)"`) to obtain the population-level trend.
Approximate 95% CI: `fit ± 1.96 × se.fit`.

### KPI — observed mean biomass
Arithmetic mean of `value` across all reefs, computed separately for each of
the most recent 5 survey years, then averaged. This is the observed mean (not
the GAM-smoothed value) and is reported with its SD.

## Random controls
None. The GAM is deterministic given REML optimization.

## Reference value and tolerance
- Reference case: **PENDING** — Cabo Pulmo, 2023.
  Source: `ltem_report/reports/cabo_pulmo_biodiversidad/cabo_pulmo_resumen_anual.csv`
  Provisional (not yet human-verified): mean biomass 2023 ≈ 11.0 g/m²
- Tolerance: PENDING (to be set with human-verified value).
- Status: PENDING — do NOT use as reference until verified by Edu/Fabio.
  Stored in `references/cabo_pulmo_biomass_reference.json`.

## Do-not rules
- Do NOT use `annual_time_series` MCP output for the GAM — it has already
  discarded the reef column needed for the random effect. Requires reef-level data.
- Do NOT change `k` above 10 or below `n_years - 1` — follow the reference
  implementation from `ltem_report/workshops/datamares/2026/generate_datamares_2026.R`.
- Do NOT use Gamma or Poisson family — the reference implementation uses
  Gaussian; do not change without updating SKILL.md and ltem_report.
- Do NOT report the GAM fit at the most recent year as the KPI — report the
  observed annual mean separately. The GAM is for the trend, the observed mean
  is for the KPI.
- Do NOT fit the GAM with fewer than 5 unique survey years — return
  `"insufficient_data"`.
- Do NOT impute missing reef-year combinations.

## Validation checklist
- [ ] self-consistency: run twice on the same input → identical fit/lwr/upr.
- [ ] reference: KPI mean biomass for Cabo Pulmo 2023 matches `references/` value
      within tolerance (PENDING until reference is set).
- [ ] coherence: GAM trend direction matches the visual pattern of the annual means.
      Deviance explained reported in method metadata.

## Success criteria
A complete fish biomass analysis includes:
- KPI: observed mean biomass (g/m²) for the most recent 5 survey years ± SD.
- Trend: GAM smooth over full year range with 95% CI, deviance explained.
- Observed annual means ± SE for overlaying on the trend plot.
- Number of unique reefs and survey years used.
- Behavioral functional-group breakdown per year × group (if `data_behavioral` provided), mapped to `TrophicYear`.
- Biomass by taxonomic family as time series year × family (if `data_family` provided).
- Biomass by species ranked by mean biomass (if `data_species` provided).
