---
name: erddap-sst-anomaly
version: 0.1.0
tier: 1
description: >
  Assess thermal conditions and warming trends at a marine protected area and
  its surrounding Large Marine Ecosystem, reporting annual SST anomalies at
  local and regional scales. Fires on questions about ocean warming near an AMP,
  thermal stress on reef communities, El Niño/La Niña impacts on a specific
  protected area, or how local sea surface temperature compares to the regional
  trend.
inputs:
  mpa:
    type: string
    required: false
    description: >
      Nombre del AMP tal como aparece en amp_geometry_lookup.csv (ej. "Cabo Pulmo").
      Usado por skill.R para obtener geometry_local vía get_amp_geometry(mpa).
      Si se omite, skill.R no puede recortar los datos y fallará.
acquire:
  # El orquestador llama al MCP de ERDDAP (dos calls: sst y anom) y los manda
  # en el body fusionados. Dataset: ncdcOisst21Agg_LonPM180 (OISST v2.1, 0.25°).
  - source: payload
    as: data
    provider:
      server: erddap
      tool: get_data
      args:
        variable: sst
        sst_var: sst
    columns:
      - lat
      - lon
      - time
      - sst
      - anom
  # geometry_local y geometry_regional NO vienen del orquestador.
  # skill.R las obtiene internamente:
  #   geometry_local    <- get_amp_geometry(mpa)      # shared/spatial_join/spatial_join.R
  #   geometry_regional <- get_lme_geometry(lme_name) # ídem, cached en shared/geometries/lme/
# Sin `output.table`: run_skill() devuelve un solo data.frame con ambas escalas.
# Skill determinista — media aritmética anual, sin bootstrap.
# MHW (kpi_mhw_days_per_yr) → skill separada erddap-mhw (issue #8 cerrado).
comparable_value: [sst_media, anomalia_media]
reference: references/cabo_pulmo_sst_reference.json
validation:
  params: {}
depends_on: []
---

# ERDDAP SST Anomaly — Thermal context for MPAs

## Purpose
Answers whether an AMP is experiencing unusual thermal conditions relative to
its historical baseline and whether local anomalies track or diverge from the
regional (LME) signal — providing the thermal context needed to interpret reef
health and fishing pressure indices alongside other skills.

## Data contract (minimal interface, NOT the local file)

The orchestrator calls the ERDDAP MCP twice and merges the results before
passing data to this skill:

```
get_data(variable="sst", sst_var="sst",  region=<region>, date_start=, date_end=)
get_data(variable="sst", sst_var="anom", region=<region>, date_start=, date_end=)
```

- Input `data`: a data.frame carrying, per observation (one row per pixel-day):
  - `lat`, `lon`  — pixel center coordinates (OISST 0.25° grid, WGS84)
  - `time`        — date (daily)
  - `sst`         — sea surface temperature (°C)
  - `anom`        — SST anomaly vs NOAA 1971–2000 climatology (°C)
- `geometry_local`    — sf object for the AMP polygon, from `get_amp_geometry()`
- `geometry_regional` — sf object for the LME polygon, from `get_lme_geometry()`

- Missing-data rule: rows where `sst` or `anom` is `NA` are excluded before
  any aggregation. Years where `cobertura_pct < 50` (fewer than half the
  expected pixel-days have valid data) are returned as `NA` with a warning —
  never silently averaged with reduced coverage.
- Aggregation unit: **pixel-day** → annual mean per scale. Fixed, not optional.

## Method (fixed, no degrees of freedom)

Computation steps, applied identically at both scales:

1. `clip_to_geometry(data, geometry_local)`   → `data_local`
2. `clip_to_geometry(data, geometry_regional)` → `data_regional`
3. For each scale and each calendar year:
   a. Exclude rows with `NA` in `sst` or `anom`
   b. Compute `cobertura_pct` = valid pixel-days / expected pixel-days × 100
   c. If `cobertura_pct < 50`: set `sst_media = NA`, `anomalia_media = NA`,
      emit `warning()` with year and coverage value
   d. Otherwise:
      - `sst_media`      = `mean(sst)` across all valid pixel-days in the year
      - `anomalia_media` = `mean(anom)` across all valid pixel-days in the year
      - `n_pixels`       = number of unique lat/lon pairs within the polygon

- Anomaly baseline: **NOAA 1971–2000 climatology**, embedded in the OISST
  `anom` variable (`ncdcOisst21Agg_LonPM180`, NOAA CoastWatch ERDDAP). Fixed —
  do not recompute from `sst`.
- Dataset: OISST v2.1, 0.25° resolution, daily. Source:
  `ncdcOisst21Agg_LonPM180` on `https://coastwatch.pfeg.noaa.gov/erddap`.

## Random controls
Not applicable — deterministic skill (spatial and temporal averaging only,
no bootstrap or stochastic step).

## Reference value and tolerance
- Reference case: **PENDING** — mean annual SST anomaly for Cabo Pulmo
  (local scale, year to be defined) → expected value to be verified by Edu/Fabio
  against published records or direct OISST query.
- Tolerance: PENDING (to be set with reference value; expected ± 0.05°C given
  deterministic averaging).
- Status: PENDING. Do NOT invent a reference value. Stored in
  `references/cabo_pulmo_sst_reference.json` with `status: PENDING`.

## Do-not rules
- Do NOT recompute anomalies from `sst` by subtracting an in-sample mean —
  use the NOAA `anom` variable with its fixed 1971–2000 baseline. Any other
  baseline changes the ecological interpretation.
- Do NOT report a year where `cobertura_pct < 50` as a valid value —
  return `NA` and emit a warning. Low coverage is common in the Gulf of Mexico
  during cloudy seasons and must be flagged, not averaged away.
- Do NOT average local and regional anomalies together or report a single
  "combined" value — the two scales answer different questions and must always
  be reported separately.
- Do NOT interpret small polygons (n_pixels < 4) as representative — OISST
  resolution (0.25°, ~25 km) is coarse relative to small AMPs. Flag in output
  when n_pixels < 4.

## Validation checklist
- [ ] self-consistency: run N times on fixed data, outputs match within 0.01°C.
- [ ] reference: output matches `references/cabo_pulmo_sst_reference.json`
      within tolerance. PENDING → SKIP with disclosure until verified.
- [ ] coherence: output declares `method` and `params` matching this contract.

## Success criteria
A complete SST anomaly analysis includes:
- Annual series of `sst_media` and `anomalia_media` for both scales (local AMP
  and regional LME), covering the full available period (1981–present).
- `cobertura_pct` and `n_pixels` reported per year and scale.
- `geometry_source` attribute documented in output (`"WDPA"` or
  `"CONANP_pending_review"`).
- Ecological interpretation: years with `anomalia_media > +0.5°C` flagged as
  potentially stressful; sustained anomalies (≥ 3 consecutive years positive)
  flagged as warming signal.
- Comparison of local vs regional trend: note whether the AMP tracks the LME
  or diverges (local upwelling, coastal effects).

---

## Planned scale architecture — PENDING: gradilla costera

> Este bloque documenta la arquitectura objetivo del MVP. No modifica el
> contrato actual. Implementar cuando la gradilla esté disponible.

### Cambio de escala local
- **Actual**: `clip_to_geometry(data, geometry_local)` con polígono del AMP (sf via `get_amp_geometry()`)
- **Planeado**: extraer valores SST/anom en las celdas de la gradilla donde `nombre_amp == <amp_name>`
- La gradilla es un objeto vectorial sf (polígonos), NO un raster
- Extracción: centroide de cada celda de la gradilla como punto de extracción sobre el raster ERDDAP (resolución OISST 0.25° ≈ 25 km, probablemente más fina que la gradilla)
- Si se quiere promedio dentro del polígono de cada celda en lugar del valor puntual, usar extracción por polígono en vez de centroide — decisión pendiente

### Cambio de escala regional
- **Actual**: `clip_to_geometry(data, geometry_regional)` con polígono del LME (sf via `get_lme_geometry()`)
- **Planeado**: extraer valores SST/anom en las celdas de la gradilla donde `region_id == <region>`, donde `region_id` proviene de `conapesca-lfo-regions`
- El valor regional de un AMP = promedio de las celdas de la gradilla de su región de manejo

### Lo que NO cambia
- Fórmula de agregación: `mean(sst)`, `mean(anom)` por año — idéntica
- Regla de cobertura (`cobertura_pct < 50` → NA)
- Baseline de anomalía: NOAA 1971–2000 climatología embebida en `anom`
- Outputs: misma estructura, solo cambia la fuente de la geometría

### Dependencias para implementar
- [ ] Gradilla costera disponible (objeto sf con columnas `nombre_amp`, `region_id`)
- [ ] `conapesca-lfo-regions` ejecutado para obtener asignación de región por celda
- [ ] Decisión: extracción por centroide vs. por polígono de celda
