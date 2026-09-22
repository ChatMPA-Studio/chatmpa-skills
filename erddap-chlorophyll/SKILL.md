---
name: erddap-chlorophyll
version: 0.2.0
tier: 1
description: >
  Assess primary productivity and phytoplankton trends at a marine protected
  area and its surrounding Large Marine Ecosystem, reporting annual chlorophyll-a
  geometric means and anomalies at local and regional scales. Fires on questions
  about ocean productivity near an AMP, upwelling strength, food availability
  for fish communities, nutrient conditions, or how local chlorophyll compares
  to regional patterns.
inputs:
  mpa:
    type: string
    required: false
    description: >
      Nombre del AMP tal como aparece en amp_geometry_lookup.csv (ej. "Cabo Pulmo").
      No se usa para recortar datos (ver bbox_local) — solo para que skill.R
      reporte geometry_source (WDPA vs CONANP_pending_review) en el output.
  bbox_local:
    type: array
    required: true
    description: >
      [lon_min, lon_max, lat_min, lat_max] del AMP. Debe resolverse ANTES de
      llamar a esta skill, buscando `mpa` en
      shared/geometries/amp_bbox_lookup.csv (chatmpa-mvp) — generado por
      shared/geometries/generate_bbox_lookups.R a partir de la misma geometría
      que usa get_amp_geometry(). No se calcula en tiempo real.
  lme:
    type: string
    required: false
    default: "Gulf of California"
    description: >
      Nombre del LME (Large Marine Ecosystem) para la escala regional, p. ej.
      "Gulf of California", "Gulf of Mexico". Usado para reportar
      geometry_source regional y para resolver bbox_regional.
  bbox_regional:
    type: array
    required: false
    description: >
      [lon_min, lon_max, lat_min, lat_max] del LME indicado en `lme`, resuelto
      de antemano contra shared/geometries/lme_bbox_lookup.csv. Si se omite,
      no se calcula la escala regional (solo local).
  date_range:
    type: date_range
    required: false
    default: ["2003-01-01", "today"]
    description: >
      Rango de fechas [inicio, fin] para la consulta. MODIS Aqua 8-day
      composites inician en 2003. "today" debe resolverse a la fecha actual
      al momento de la llamada.
acquire:
  # El MCP de ERDDAP promedia espacialmente del lado del servidor
  # (aggregate_spatial=TRUE) y regresa un valor por composite de 8 días — no
  # pixel-composite crudo. bbox_local/bbox_regional ya vienen resueltos (ver
  # inputs) — este acquire nunca calcula geometría.
  - source: payload
    as: data_local
    provider:
      server: erddap
      tool: get_data
      args:
        variable: chlorophyll
        aggregate_spatial: true
      params:
        bbox:       bbox_local
        date_range: date_range
    columns:
      - time
      - chlorophyll
  - source: payload
    as: data_regional
    required: false
    provider:
      server: erddap
      tool: get_data
      args:
        variable: chlorophyll
        aggregate_spatial: true
      params:
        bbox:       bbox_regional
        date_range: date_range
    columns:
      - time
      - chlorophyll
output:
  table: chl_annual
  columns: [year, escala, chl_geomean, anomalia_log10, anomalia_mgm3, n_pixels, cobertura_pct, prod_flag]
# Skill determinista — media geométrica log10, sin bootstrap.
comparable_value: [chl_geomean, anomalia_log10]
reference: references/cabo_pulmo_chl_reference.json
validation:
  params: {}
depends_on: []
---

# ERDDAP Chlorophyll-a — Primary productivity context for MPAs

## Purpose
Answers whether primary productivity at an AMP is above or below its historical
baseline and whether it tracks or diverges from the regional (LME) signal —
providing the bottom-up ecological context needed to interpret reef biomass and
fishing pressure alongside other skills. Chlorophyll-a is the proxy for
phytoplankton biomass and primary productivity.

## Data contract (minimal interface, NOT the local file)

The orchestrator calls the ERDDAP MCP once per scale, with spatial averaging
done server-side:

```
get_data(variable="chlorophyll", aggregate_spatial=true,
         bbox=<bbox_local>,    date_range=<date_range>) → data_local
get_data(variable="chlorophyll", aggregate_spatial=true,
         bbox=<bbox_regional>, date_range=<date_range>) → data_regional (optional)
```

- `data_local` / `data_regional`: one row **per 8-day composite** (not per
  pixel-composite — the MCP already averaged over all pixels in the bbox):
  - `time`        — start date of the 8-day composite period
  - `chlorophyll` — chlorophyll-a concentration (mg/m³), spatial mean over
    the bbox; `NA` over clouds
- `bbox_local` / `bbox_regional` are resolved **before** this skill runs, from
  `amp_bbox_lookup.csv` / `lme_bbox_lookup.csv` (`shared/geometries/` in
  `chatmpa-mvp`) — see `inputs` above. skill.R never computes a bbox itself.
- `mpa` / `lme` are passed through unchanged to `skill.R` purely so it can
  call `get_amp_geometry()` / `get_lme_geometry()` for `geometry_source`
  metadata — not for spatial filtering.

- Missing-data rule: rows where `chlorophyll` is `NA` or ≤ 0 are excluded
  before any aggregation. Cloud cover routinely causes large gaps — this is
  expected and handled via `cobertura_pct`. Years where `cobertura_pct < 30`
  are returned as `NA` with a warning. The 30% threshold (lower than SST's 50%)
  reflects the expected cloud-driven gaps in 8-day composites.
- Aggregation unit: **8-day composite** (already bbox-averaged) → annual
  geometric mean per scale. Fixed, not optional.
- Dataset: MODIS Aqua Science Quality 8-day composites, 4 km resolution,
  2003–present. Source: `erdMH1chla8day_R202SQ` on
  `https://coastwatch.pfeg.noaa.gov/erddap`.

## Method (fixed, no degrees of freedom)

Chlorophyll-a is log-normally distributed — arithmetic means overweight bloom
events and must not be used. All averaging is done in log10 space.

Computation steps, applied identically at both scales:

1. For each scale and each calendar year:
   a. Exclude rows where `chlorophyll` is `NA` or ≤ 0
   b. Compute `cobertura_pct` = valid composites / 46 (expected composites/year) × 100
   c. If `cobertura_pct < 30`: set outputs to `NA`, emit `warning()` with year
      and coverage value
   d. Otherwise compute the **annual geometric mean**:
      `chl_geomean = 10 ^ mean(log10(chlorophyll))`
2. Compute the **anomaly** relative to the baseline period (2003–2020):
   - Baseline geometric mean per scale:
     `chl_baseline = 10 ^ mean(log10(chlorophyll))` over all valid
     composites across 2003–2020
   - Annual anomaly (log10 units, interpretable as order-of-magnitude deviation):
     `anomalia_log10 = log10(chl_geomean) - log10(chl_baseline)`
   - Also report in natural units for interpretability:
     `anomalia_mgm3 = chl_geomean - chl_baseline`
- Baseline period: **2003–2020** (fixed). Do not adjust to match the
  requested analysis window.

## Random controls
Not applicable — deterministic skill (log-space averaging only, no bootstrap
or stochastic step).

## Reference value and tolerance
- Reference case: **PENDING** — annual geometric mean chl-a for Cabo Pulmo
  (local scale, year to be defined) → expected value to be verified by Edu/Fabio
  against direct MODIS query or published productivity estimates for the area.
- Tolerance: PENDING (expected ± 0.02 log10 units given deterministic averaging).
- Status: PENDING. Do NOT invent a reference value. Stored in
  `references/cabo_pulmo_chl_reference.json` with `status: PENDING`.

## Do-not rules
- Do NOT use arithmetic mean of raw chlorophyll values — the distribution is
  log-normal and bloom events create extreme outliers that dominate the mean.
  Always average in log10 space and back-transform.
- Do NOT report a year where `cobertura_pct < 30` as a valid value —
  return `NA` and emit a warning. Gulf of Mexico and enclosed coastal areas
  can have very high cloud cover for extended periods.
- Do NOT recompute the baseline from a different period — the 2003–2020
  baseline is fixed. Changing the baseline period changes anomaly values and
  makes comparisons across sites and skills inconsistent.
- Do NOT average local and regional values together — they answer different
  questions and must always be reported separately.
- Do NOT interpret `anomalia_log10` without noting the baseline period and
  `cobertura_pct`. A positive anomaly in a low-coverage year is unreliable.
- Do NOT compute `bbox_local` / `bbox_regional` inside `skill.R` or at
  request time — they must come from the precomputed lookup tables. Adding a
  new AMP means re-running `generate_bbox_lookups.R`, not adding logic here.

## Validation checklist
- [ ] self-consistency: run N times on fixed data, outputs match within
      0.001 log10 units.
- [ ] reference: output matches `references/cabo_pulmo_chl_reference.json`
      within tolerance. PENDING → SKIP with disclosure until verified.
- [ ] coherence: output declares `method` and `params` matching this contract.

## Success criteria
A complete chlorophyll analysis includes:
- Annual series of `chl_geomean`, `anomalia_log10`, and `anomalia_mgm3` for
  both scales (local AMP and regional LME), covering 2003–present.
- `cobertura_pct` reported per year and scale.
- `geometry_source` attribute documented in output (`"WDPA"` or
  `"CONANP_pending_review"`).
- Baseline period (2003–2020) explicitly stated in any reported result.
- Ecological interpretation: `anomalia_log10 > +0.3` (roughly 2× baseline)
  flagged as high-productivity event; `< -0.3` (roughly 0.5× baseline) flagged
  as low-productivity. Comparison of local vs regional signal noted (local
  upwelling decoupling is common along Baja California).

---

## Precisión del bbox — nota, no bloqueo

`bbox_local` es el rectángulo mínimo que contiene el polígono del AMP, no el
polígono exacto. Dado que MODIS (4 km) es más fino que OISST (25 km), el
efecto de esta simplificación en `chl_geomean` es aún menor que en
`erddap-sst-anomaly`. Si en el futuro se necesita precisión de polígono
exacto, la alternativa es una gradilla costera fina — no implementada
todavía, y no bloquea el uso actual.
