---
name: ltem-fish-biomass
version: 0.3.1
tier: 2
description: >
  Assess fish standing stock and recovery trends at a marine protected area,
  reporting mean fish biomass (T/ha) and its temporal trend from the LTEM
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
  scalars:
    mk_p_value:         numeric    # Mann-Kendall two-sided p-value; NA if < 8 survey years
    mk_slope_direction: character  # "positive" | "negative" | "none" | "insufficient_data"
    mk_label:           character  # human-readable trend category (Spanish)
# GAM con REML: determinista dado el ajuste. El KPI es media aritmética.
comparable_value: [mean_biomass_t_ha, se_t_ha]
reference: references/cabo_pulmo_biomass_reference.json
validation:
  params:
    region: Cabo Pulmo
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
- `value` — mean fish biomass (T/ha) for that reef-year (averaged across transects).
  Already in T/ha: skill.R does not convert it.
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
- `mean_biomass` — mean biomass (T/ha); SUM per transect → AVG per reef → AVG per year.
- `n_transects` — total transects contributing across reefs.

Optional input — biomass by taxonomic family (`data_family`), one row per year × family.
Feeds `GET /species/family-biomass`. Unit: T/ha (consistent with `get_biomass_data`).
The tool returns ALL families — filtering to specific families (e.g. Serranidae, Lutjanidae,
Carangidae) is the caller's responsibility, analogous to how top-N selection is delegated
to the caller for `data_species`.
- `year` — survey year
- `family` — taxonomic family
- `mean_biomass` — mean biomass (T/ha); SUM per transect then AVG across transects
- `n_transects` — number of transects contributing

Optional input — biomass by species (`data_species`), one row per species.
Feeds `GET /biomass/top-species`. Unit: T/ha (consistent with `get_biomass_data`).
Biomass is collapsed across years unless `year` is specified. Ranking (top-N) is the
caller's responsibility.
- `species_id` — IDSpecies from ltem_historical_database
- `species_name` — scientific name
- `trophic_group` — TrophicGroup from ltem_historical_database
- `mean_biomass` — mean biomass (T/ha); SUM per transect then AVG across transects
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
- Aggregation: sum per transect, then within-reef mean across transects for each year
- Unit: T/ha. The LTEM `Biomass` column is loaded as Quantity × a × Size^b / (Area × 100) = g/m² ÷ 100 = T/ha; the skill does not convert it.

Not applied (by the MCP or by this skill): size outlier removal (`size_check()`),
the Corredor exclusion of Haemulidae/Carangidae with biomass > 3, and the filter of
reefs monitored ≥ 5 years. `ltem_report` applies them in its own analysis
(`04-full_trends_analysis.R`), so its values are not directly comparable with this
skill's (ltem-db-mcp#10).

Data source: Centro para la Biodiversidad Marina y la Conservación [CBMC] (2026),
LTEM database.

Missing-data rule: if a reef-year combination is missing (reef not surveyed in
a given year), that row is absent — do not impute. The GAM handles irregular
sampling via the smooth. Require at least 5 unique years across all reefs to
fit the model; otherwise return `"insufficient_data"`.

## Method (fixed, no degrees of freedom)

### Trend: GAM with reef random effect
Generalized additive model fitted by REML (Wood, 2011, 2017).
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

### Mann-Kendall trend label
Applied to the **observed annual means** (not the GAM smooth): for each unique
survey year, use the mean of `value` across all reefs (already computed in the
annual means step), yielding one data point per year. Run a two-sided
Mann-Kendall test (Mann, 1945; Kendall, 1975) on this chronologically-ordered
series. Estimate the slope via the Theil-Sen method (Theil, 1950; Sen, 1968).

**Minimum data requirement:** if fewer than 8 unique survey years are available,
skip the test and return:
- `mk_p_value = NA`
- `mk_slope_direction = "insufficient_data"`
- `mk_label = "Datos insuficientes para tendencia"`

**Classification rules (when n_years ≥ 8):**
- `p < 0.05` and Sen's slope > 0 → direction = `"positive"` → label = `"Biomasa íctica en aumento"`
- `p < 0.05` and Sen's slope < 0 → direction = `"negative"` → label = `"Biomasa íctica en declive"`
- `p ≥ 0.05`                     → direction = `"none"`     → label = `"Biomasa íctica estable"`

**Implementation:** Mann-Kendall p-value via `mk_trend()` (`Kendall::MannKendall`,
`shared/interpretation/interpret.R`); slope with `trend::sens.slope()`; the direction
is the sign of the Sen slope. Packages `Kendall` and `trend` must be installed.

### Interpretation
Computed on the observed annual means:
- Before/after comparison (`before_after()`): first 5 survey years vs. last 5.
- Mann-Kendall test via `mk_trend()` (minimum number of years as set in `mk_trend()`).
- Status: `"positive"` if the direction is increasing and Mann-Kendall p < 0.10;
  `"negative"` if decreasing and p < 0.10; otherwise `"neutral"`. This softer
  p < 0.10 signal is separate from the `mk_*` label above (p < 0.05).

## Random controls
None. The GAM is deterministic given REML optimization.

## Reference value and tolerance
- Reference cases: 2 (`mean_biomass_t_ha`, `se_t_ha`) in
  `references/cabo_pulmo_biomass_reference.json`.
- Case: Cabo Pulmo region, full series; the 2023 row of `annual_means` (mean
  across reefs) is compared.
- Expected values: 3.0709 T/ha (mean) and 0.9438 T/ha (SE), verified by Carolina
  (2026-10-01) with an independent calculation on LTEM server data
  (`get_biomass_data`, snapshot 2026-10-01; data up to the November 2025 survey).
- Tolerance: ±0.00005 (the skill rounds to 4 decimals).
- Seed: not applicable (deterministic).
- Status: VERIFIED.

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
- Do NOT run Mann-Kendall on the GAM smooth — run it on the observed annual
  means (one value per year, averaged across reefs). The smooth is for the trend
  plot; MK is the inferential test.
- Do NOT run Mann-Kendall with fewer than 8 unique survey years — return
  `"insufficient_data"` in all three MK fields.

## Validation checklist
- [ ] self-consistency: run twice on the same input → identical fit/lwr/upr.
- [ ] reference: mean biomass for Cabo Pulmo 2023 matches the `references/` value
      within tolerance.
- [ ] coherence: GAM trend direction matches the visual pattern of the annual means.
      Deviance explained reported in method metadata.

## Success criteria
A complete fish biomass analysis includes:
- KPI: observed mean biomass (T/ha) for the most recent 5 survey years ± SD.
- Trend: GAM smooth over full year range with 95% CI, deviance explained.
- Observed annual means ± SE for overlaying on the trend plot.
- Number of unique reefs and survey years used.
- Behavioral functional-group breakdown per year × group (if `data_behavioral` provided), mapped to `TrophicYear`.
- Biomass by taxonomic family as time series year × family (if `data_family` provided).
- Biomass by species ranked by mean biomass (if `data_species` provided).
- Mann-Kendall scalars (`mk_p_value`, `mk_slope_direction`, `mk_label`) always
  present in output, even when `"insufficient_data"` (< 8 survey years).

## References
- Centro para la Biodiversidad Marina y la Conservación. (2026). *Programa de
  Monitoreo Ecológico de Largo Plazo (LTEM)* [Datos sin publicar].
- Kendall, M. G. (1975). *Rank correlation methods* (4th ed.). Charles Griffin.
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica, 13*(3),
  245–259. https://doi.org/10.2307/1907187
- McLeod, A. I. (2025). *Kendall: Kendall rank correlation and Mann-Kendall trend test*
  (Version 2.2.2) [R package]. https://CRAN.R-project.org/package=Kendall
- Pohlert, T. (2026). *trend: Non-parametric trend tests and change-point detection*
  (Version 1.1.8) [R package]. https://CRAN.R-project.org/package=trend
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau.
  *Journal of the American Statistical Association, 63*(324), 1379–1389.
  https://doi.org/10.1080/01621459.1968.10480934
- Theil, H. (1950). A rank-invariant method of linear and polynomial regression
  analysis, I, II, III. *Proceedings of the Koninklijke Nederlandse Akademie van
  Wetenschappen, 53*, 386–392, 521–525, 1397–1412. Reprinted in B. Raj & J. Koerts
  (Eds.), *Henri Theil's contributions to economics and econometrics* (pp. 345–381).
  Springer, 1992. https://doi.org/10.1007/978-94-011-2546-8_20
- Wood, S. N. (2011). Fast stable restricted maximum likelihood and marginal
  likelihood estimation of semiparametric generalized linear models. *Journal of
  the Royal Statistical Society: Series B (Statistical Methodology), 73*(1), 3–36.
  https://doi.org/10.1111/j.1467-9868.2010.00749.x
- Wood, S. N. (2017). *Generalized additive models: An introduction with R* (2nd ed.).
  Chapman and Hall/CRC. https://doi.org/10.1201/9781315370279
