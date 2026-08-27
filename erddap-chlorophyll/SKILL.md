---
name: erddap-chlorophyll
version: 0.1.0
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
      Usado por skill.R para obtener geometry_local vía get_amp_geometry(mpa).
      Si se omite, skill.R no puede recortar los datos y fallará.
acquire:
  # El orquestador llama al MCP de ERDDAP y manda los datos en el body.
  # Dataset: erdMH1chla8day_R202SQ (MODIS Aqua 8-day, 4 km).
  - source: payload
    as: data
    provider:
      server: erddap
      tool: get_data
      args:
        variable: chlorophyll
    columns:
      - lat
      - lon
      - time
      - chlorophyll
  # geometry_local y geometry_regional NO vienen del orquestador.
  # skill.R las obtiene internamente:
  #   geometry_local    <- get_amp_geometry(mpa)      # shared/spatial_join/spatial_join.R
  #   geometry_regional <- get_lme_geometry(lme_name) # ídem, cached en shared/geometries/lme/
# Sin `output.table`: run_skill() devuelve un solo data.frame con ambas escalas.
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

The orchestrator calls the ERDDAP MCP once before passing data to this skill:

```
get_data(variable="chlorophyll", region=<region>, date_start=, date_end=)
```

- Input `data`: a data.frame carrying, per observation (one row per pixel per
  8-day composite):
  - `lat`, `lon`      — pixel center coordinates (MODIS 4 km grid, WGS84)
  - `time`            — start date of the 8-day composite period
  - `chlorophyll`     — chlorophyll-a concentration (mg/m³); NA over clouds
- `geometry_local`    — sf object for the AMP polygon, from `get_amp_geometry()`
- `geometry_regional` — sf object for the LME polygon, from `get_lme_geometry()`

- Missing-data rule: rows where `chlorophyll` is `NA` or ≤ 0 are excluded
  before any aggregation. Cloud cover routinely causes large gaps — this is
  expected and handled via `cobertura_pct`. Years where `cobertura_pct < 30`
  are returned as `NA` with a warning. The 30% threshold (lower than SST's 50%)
  reflects the expected cloud-driven gaps in 8-day composites.
- Aggregation unit: **pixel per 8-day composite** → annual geometric mean per
  scale. Fixed, not optional.
- Dataset: MODIS Aqua Science Quality 8-day composites, 4 km resolution,
  2003–present. Source: `erdMH1chla8day_R202SQ` on
  `https://coastwatch.pfeg.noaa.gov/erddap`.

## Method (fixed, no degrees of freedom)

Chlorophyll-a is log-normally distributed — arithmetic means overweight bloom
events and must not be used. All averaging is done in log10 space.

Computation steps, applied identically at both scales:

1. `clip_to_geometry(data, geometry_local)`    → `data_local`
2. `clip_to_geometry(data, geometry_regional)` → `data_regional`
3. For each scale and each calendar year:
   a. Exclude rows where `chlorophyll` is `NA` or ≤ 0
   b. Compute `cobertura_pct` = valid pixel-composites / expected pixel-composites × 100
      (expected = n_pixels_within_polygon × 46 composites/year)
   c. If `cobertura_pct < 30`: set outputs to `NA`, emit `warning()` with year
      and coverage value
   d. Otherwise compute the **annual geometric mean**:
      `chl_geomean = 10 ^ mean(log10(chlorophyll))`
4. Compute the **anomaly** relative to the baseline period (2003–2020):
   - Baseline geometric mean per scale:
     `chl_baseline = 10 ^ mean(log10(chlorophyll))` over all valid
     pixel-composites within the polygon across 2003–2020
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
- Do NOT flag n_pixels < 4 as a warning for chlorophyll as aggressively as for
  SST — MODIS resolution (4 km) is finer than OISST (25 km), so small AMPs
  still have meaningful pixel coverage.

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
- `cobertura_pct` and `n_pixels` reported per year and scale.
- `geometry_source` attribute documented in output (`"WDPA"` or
  `"CONANP_pending_review"`).
- Baseline period (2003–2020) explicitly stated in any reported result.
- Ecological interpretation: `anomalia_log10 > +0.3` (roughly 2× baseline)
  flagged as high-productivity event; `< -0.3` (roughly 0.5× baseline) flagged
  as low-productivity. Comparison of local vs regional signal noted (local
  upwelling decoupling is common along Baja California).

---

## Planned scale architecture — PENDING: gradilla costera

> Este bloque documenta la arquitectura objetivo del MVP. No modifica el
> contrato actual. Implementar cuando la gradilla esté disponible.

### Cambio de escala local
- **Actual**: `clip_to_geometry(data, geometry_local)` con polígono del AMP
- **Planeado**: extraer valores de clorofila en celdas de la gradilla donde `nombre_amp == <amp_name>`
- Extracción: centroide de cada celda como punto sobre el raster ERDDAP (MODIS 4 km, probablemente más fino que la gradilla)
- Si se quiere promedio por polígono de celda en lugar del valor puntual, usar extracción por polígono — decisión pendiente

### Cambio de escala regional
- **Actual**: `clip_to_geometry(data, geometry_regional)` con polígono del LME
- **Planeado**: extraer valores en celdas de la gradilla donde `region_id == <region>` (de `conapesca-lfo-regions`)

### Lo que NO cambia
- Fórmula: media geométrica log₁₀, anomalía log₁₀ vs. baseline 2003–2020 — idéntica
- Regla de cobertura (`cobertura_pct < 50` → NA)
- Outputs: misma estructura

### Dependencias para implementar
- [ ] Gradilla costera disponible (sf con `nombre_amp`, `region_id`)
- [ ] `conapesca-lfo-regions` ejecutado
- [ ] Decisión: extracción por centroide vs. por polígono de celda
