---
name: erddap-pp
version: 0.1.0
tier: 1
description: >
  Assess primary productivity levels and trends at a marine protected area and
  its surrounding Large Marine Ecosystem, reporting annual net primary production
  geometric means and anomalies at local and regional scales. Fires on questions
  about ocean productivity near an AMP, phytoplankton growth efficiency, carbon
  flux into the food web, or how local production compares to regional patterns.
inputs: {}
acquire:
  # El orquestador llama al MCP de ERDDAP y manda los datos en el body.
  # Dataset: erdMH1pp8day (MODIS Aqua 8-day NPP, 4 km).
  - source: payload
    as: data
    provider:
      server: erddap
      tool: get_data
      args:
        variable: primary_productivity
    columns:
      - lat
      - lon
      - time
      - pp
  - source: payload
    as: geometry_local
    type: sf
  - source: payload
    as: geometry_regional
    type: sf
# Sin `output.table`: run_skill() devuelve un solo data.frame con ambas escalas.
# Skill determinista — media geométrica log10, sin bootstrap.
comparable_value: [pp_geomean, anomalia_log10]
reference: references/cabo_pulmo_pp_reference.json
validation:
  params: {}
depends_on: []
---

# ERDDAP Primary Productivity — Production context for MPAs

## Purpose
Answers whether net primary production at an AMP is above or below its
historical baseline and whether it tracks or diverges from the regional (LME)
signal — providing the production context needed to interpret reef biomass and
trophic structure alongside other skills. Net primary production (NPP) is the
rate at which phytoplankton fix carbon, expressed in mgC/m²/day.

## Data contract (minimal interface, NOT the local file)

The orchestrator calls the ERDDAP MCP once before passing data to this skill:

```
get_data(variable="primary_productivity", region=<region>, date_start=, date_end=)
```

- Input `data`: a data.frame carrying, per observation (one row per pixel per
  8-day composite):
  - `lat`, `lon` — pixel center coordinates (MODIS 4 km grid, WGS84)
  - `time`       — start date of the 8-day composite period
  - `pp`         — net primary production (mgC/m²/day); NA over clouds
- `geometry_local`    — sf object for the AMP polygon, from `get_amp_geometry()`
- `geometry_regional` — sf object for the LME polygon, from `get_lme_geometry()`

- Missing-data rule: rows where `pp` is `NA` or ≤ 0 are excluded before any
  aggregation. Years where `cobertura_pct < 30` are returned as `NA` with a
  warning. The 30% threshold reflects expected cloud-driven gaps in 8-day
  composites (same as chlorophyll).
- Aggregation unit: **pixel per 8-day composite** → annual geometric mean per
  scale. Fixed, not optional.
- Dataset: MODIS Aqua 8-day composite NPP, 4 km resolution, 2003–present.
  Source: `erdMH1pp8day` on `https://coastwatch.pfeg.noaa.gov/erddap`.

## Method (fixed, no degrees of freedom)

NPP is log-normally distributed — arithmetic means overweight high-production
events and must not be used. All averaging is done in log10 space.

Computation steps, applied identically at both scales:

1. `clip_to_geometry(data, geometry_local)`    → `data_local`
2. `clip_to_geometry(data, geometry_regional)` → `data_regional`
3. For each scale and each calendar year:
   a. Exclude rows where `pp` is `NA` or ≤ 0
   b. Compute `cobertura_pct` = valid pixel-composites / expected pixel-composites × 100
      (expected = n_pixels_within_polygon × 46 composites/year)
   c. If `cobertura_pct < 30`: set outputs to `NA`, emit `warning()` with year
      and coverage value
   d. Otherwise compute the **annual geometric mean**:
      `pp_geomean = 10 ^ mean(log10(pp))`
4. Compute the **anomaly** relative to the baseline period (2003–2020):
   - Baseline geometric mean per scale:
     `pp_baseline = 10 ^ mean(log10(pp))` over all valid pixel-composites
     within the polygon across 2003–2020
   - Annual anomaly (log10 units):
     `anomalia_log10 = log10(pp_geomean) - log10(pp_baseline)`
   - Also report in natural units for interpretability:
     `anomalia_mgcm2d = pp_geomean - pp_baseline`
- Baseline period: **2003–2020** (fixed, matching chlorophyll baseline).
  Do not adjust to match the requested analysis window.

## Random controls
Not applicable — deterministic skill (log-space averaging only, no bootstrap
or stochastic step).

## Reference value and tolerance
- Reference case: **PENDING** — annual geometric mean NPP for Cabo Pulmo
  (local scale, year to be defined) → expected value to be verified by Edu/Fabio
  against direct MODIS query or published productivity estimates for the area.
- Tolerance: PENDING (expected ± 0.02 log10 units given deterministic averaging).
- Status: PENDING. Do NOT invent a reference value. Stored in
  `references/cabo_pulmo_pp_reference.json` with `status: PENDING`.

## Do-not rules
- Do NOT use arithmetic mean of raw PP values — the distribution is log-normal
  and high-production events create extreme outliers that dominate the mean.
  Always average in log10 space and back-transform.
- Do NOT report a year where `cobertura_pct < 30` as a valid value —
  return `NA` and emit a warning.
- Do NOT recompute the baseline from a different period — the 2003–2020
  baseline is fixed and matches the chlorophyll baseline, making PP and Chl-a
  anomalies directly comparable.
- Do NOT average local and regional values together — they answer different
  questions and must always be reported separately.

## Validation checklist
- [ ] self-consistency: run N times on fixed data, outputs match within
      0.001 log10 units.
- [ ] reference: output matches `references/cabo_pulmo_pp_reference.json`
      within tolerance. PENDING → SKIP with disclosure until verified.
- [ ] coherence: output declares `method` and `params` matching this contract.

## Success criteria
A complete PP analysis includes:
- Annual series of `pp_geomean`, `anomalia_log10`, and `anomalia_mgcm2d` for
  both scales (local AMP and regional LME), covering 2003–present.
- `cobertura_pct` and `n_pixels` reported per year and scale.
- `geometry_source` attribute documented in output (`"WDPA"` or
  `"CONANP_pending_review"`).
- Baseline period (2003–2020) explicitly stated in any reported result.
- Ecological interpretation: `anomalia_log10 > +0.3` (roughly 2× baseline)
  flagged as high-production event; `< -0.3` (roughly 0.5× baseline) flagged
  as low-production. Comparison of local vs regional signal noted.

---

## Planned scale architecture — PENDING: gradilla costera

> Este bloque documenta la arquitectura objetivo del MVP. No modifica el
> contrato actual. Implementar cuando la gradilla esté disponible.

### Cambio de escala local
- **Actual**: `clip_to_geometry(data, geometry_local)` con polígono del AMP
- **Planeado**: extraer valores de PP en celdas de la gradilla donde `nombre_amp == <amp_name>`
- Extracción: centroide de cada celda como punto sobre el raster ERDDAP (resolución ~9 km, probablemente más fina que la gradilla)

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
