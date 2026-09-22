---
name: erddap-sst-anomaly
version: 0.2.0
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
    default: ["1981-09-01", "today"]
    description: >
      Rango de fechas [inicio, fin] para la consulta. OISST v2.1 inicia
      1981-09-01. "today" debe resolverse a la fecha actual al momento de la
      llamada.
acquire:
  # El MCP de ERDDAP promedia espacialmente del lado del servidor
  # (aggregate_spatial=TRUE) y regresa un valor por día — no pixel-día crudo.
  # sst_vars=[sst, anom] trae ambas variables en UNA sola llamada por escala
  # (no hacen falta dos llamadas separadas). bbox_local/bbox_regional ya
  # vienen resueltos (ver inputs) — este acquire nunca calcula geometría.
  - source: payload
    as: data_local
    provider:
      server: erddap
      tool: get_data
      args:
        variable: sst
        aggregate_spatial: true
        sst_vars: [sst, anom]
      params:
        bbox:       bbox_local
        date_range: date_range
    columns:
      - time
      - sst
      - anom
  - source: payload
    as: data_regional
    required: false
    provider:
      server: erddap
      tool: get_data
      args:
        variable: sst
        aggregate_spatial: true
        sst_vars: [sst, anom]
      params:
        bbox:       bbox_regional
        date_range: date_range
    columns:
      - time
      - sst
      - anom
output:
  table: sst_annual
  columns: [year, escala, sst_media, anomalia_media, n_pixels, cobertura_pct, stress_flag]
# Skill determinista — media aritmética anual, sin bootstrap.
# MHW (kpi_mhw_days_per_yr) → skill separada erddap-mhw.
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

The orchestrator calls the ERDDAP MCP once per scale, with spatial averaging
done server-side:

```
get_data(variable="sst", sst_vars=["sst","anom"], aggregate_spatial=true,
         bbox=<bbox_local>,    date_range=<date_range>)   → data_local
get_data(variable="sst", sst_vars=["sst","anom"], aggregate_spatial=true,
         bbox=<bbox_regional>, date_range=<date_range>)   → data_regional (optional)
```

- `data_local` / `data_regional`: one row **per day** (not per pixel-day —
  the MCP already averaged over all pixels in the bbox):
  - `time` — date (daily)
  - `sst`  — sea surface temperature (°C), spatial mean over the bbox
  - `anom` — SST anomaly vs NOAA 1971–2000 climatology (°C), spatial mean
- `bbox_local` / `bbox_regional` are resolved **before** this skill runs, from
  `amp_bbox_lookup.csv` / `lme_bbox_lookup.csv` (`shared/geometries/` in
  `chatmpa-mvp`) — see `inputs` above. skill.R never computes a bbox itself.
- `mpa` / `lme` are passed through unchanged to `skill.R` purely so it can
  call `get_amp_geometry()` / `get_lme_geometry()` for `geometry_source`
  metadata (WDPA vs CONANP_pending_review) — not for spatial filtering.

- Missing-data rule: rows where `sst` or `anom` is `NA` are excluded before
  any aggregation. Years where `cobertura_pct < 50` (fewer than half the
  expected daily values are present) are returned as `NA` with a warning —
  never silently averaged with reduced coverage.
- Aggregation unit: **day** (already bbox-averaged) → annual mean per scale.
  Fixed, not optional.

## Method (fixed, no degrees of freedom)

Computation steps, applied identically at both scales:

1. For each scale and each calendar year:
   a. Exclude rows with `NA` in `sst` or `anom`
   b. Compute `cobertura_pct` = valid days / 365 × 100
   c. If `cobertura_pct < 50`: set `sst_media = NA`, `anomalia_media = NA`,
      emit `warning()` with year and coverage value
   d. Otherwise:
      - `sst_media`      = `mean(sst)` across all valid days in the year
      - `anomalia_media` = `mean(anom)` across all valid days in the year
      - `n_pixels`       = `NA` (not applicable — data already spatially
        averaged by the MCP; there is no per-pixel count on this side)

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
- Do NOT compute `bbox_local` / `bbox_regional` inside `skill.R` or at
  request time — they must come from the precomputed lookup tables. Adding a
  new AMP means re-running `generate_bbox_lookups.R`, not adding logic here.

## Validation checklist
- [ ] self-consistency: run N times on fixed data, outputs match within 0.01°C.
- [ ] reference: output matches `references/cabo_pulmo_sst_reference.json`
      within tolerance. PENDING → SKIP with disclosure until verified.
- [ ] coherence: output declares `method` and `params` matching this contract.

## Success criteria
A complete SST anomaly analysis includes:
- Annual series of `sst_media` and `anomalia_media` for both scales (local AMP
  and regional LME), covering the full available period (1981–present).
- `cobertura_pct` reported per year and scale.
- `geometry_source` attribute documented in output (`"WDPA"` or
  `"CONANP_pending_review"`).
- Ecological interpretation: years with `anomalia_media > +0.5°C` flagged as
  potentially stressful; sustained anomalies (≥ 3 consecutive years positive)
  flagged as warming signal.
- Comparison of local vs regional trend: note whether the AMP tracks the LME
  or diverges (local upwelling, coastal effects).

---

## Precisión del bbox — nota, no bloqueo

`bbox_local` es el rectángulo mínimo que contiene el polígono del AMP, no el
polígono exacto — para AMPs con forma muy irregular puede incluir agua (o
tierra) fuera del límite real de la reserva. Dado que la resolución de OISST
(~25 km) ya es gruesa respecto a la mayoría de las AMPs mexicanas, el efecto
práctico es pequeño, pero es una simplificación real. Si en el futuro se
necesita precisión de polígono exacto (p. ej. AMPs muy alargadas o con costa
recortada), la alternativa es una gradilla costera (celdas sf finas,
`nombre_amp`/`region_id`) que reemplace el bbox por una máscara de celdas —
no implementada todavía, y no bloquea el uso actual.
