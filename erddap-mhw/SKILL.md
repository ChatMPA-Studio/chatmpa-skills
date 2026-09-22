---
name: erddap-mhw
version: 0.2.0
tier: 1
description: >
  Detect and quantify Marine Heatwave (MHW) events at a marine protected area,
  reporting the annual number of heatwave days and events using the heatwaveR
  protocol on daily OISST SST data. Fires on questions about heat stress days,
  marine heatwaves near an AMP, how many days exceeded thermal thresholds, or
  whether heatwave frequency is increasing over time. Companion skill to
  erddap-sst-anomaly — that skill reports mean temperatures; this one reports
  extreme thermal events.
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
  date_range:
    type: date_range
    required: false
    default: ["1982-01-01", "today"]
    description: >
      Rango de fechas [inicio, fin]. Debe iniciar en 1982-01-01 o antes — la
      climatología de referencia (1982–2011) necesita la serie completa desde
      ese año. "today" debe resolverse a la fecha actual al momento de la
      llamada.
acquire:
  # El MCP de ERDDAP promedia espacialmente del lado del servidor
  # (aggregate_spatial=TRUE) y regresa un valor por día — no pixel-día crudo.
  # Se necesita la serie histórica completa (desde 1982) para construir la
  # climatología de referencia con ts2clm(). bbox_local ya viene resuelto
  # (ver inputs) — este acquire nunca calcula geometría.
  - source: payload
    as: data
    provider:
      server: erddap
      tool: get_data
      args:
        variable: sst
        sst_var: sst
        aggregate_spatial: true
      params:
        bbox:       bbox_local
        date_range: date_range
    columns:
      - time
      - sst
output:
  table: mhw_annual
  columns: [year, kpi_mhw_days_per_yr, n_events_per_yr, mean_intensity_per_yr]
# Skill determinista — el algoritmo heatwaveR es reproducible dado los datos.
comparable_value: [kpi_mhw_days_per_yr, n_events_per_yr]
reference: references/cabo_pulmo_mhw_reference.json
validation:
  params: {}
depends_on: []
---

# ERDDAP Marine Heatwaves (MHW)

## Purpose
Answers how many days per year the ocean exceeded its historical thermal threshold
near an AMP, and whether heatwave frequency and intensity are changing over time.
Uses the international heatwaveR protocol to detect discrete Marine Heatwave events
from daily OISST SST data.

## Data contract (minimal interface, NOT the local file)

The orchestrator calls the ERDDAP MCP once, with spatial averaging done
server-side:

```
get_data(variable="sst", sst_var="sst", aggregate_spatial=true,
         bbox=<bbox_local>, date_range=<date_range>)
```

- `data`: one row **per day** (not per pixel-day — the MCP already averaged
  over all pixels in the bbox):
  - `time` — date (daily)
  - `sst`  — sea surface temperature (°C), spatial mean over the bbox
- `bbox_local` is resolved **before** this skill runs, from
  `amp_bbox_lookup.csv` (`shared/geometries/` in `chatmpa-mvp`) — see `inputs`
  above. skill.R never computes a bbox itself.
- `mpa` is passed through unchanged to `skill.R` purely so it can call
  `get_amp_geometry()` for `geometry_source` metadata — not for spatial
  filtering.

The series must start from 1982 — earlier dates are not available in OISST v2.1.
The climatology baseline period (1982–2011) requires at least 30 years of data.

- Missing-data rule: days with `NA` in `sst` are excluded before any
  aggregation.

## Method (fixed, no degrees of freedom)

### Step 1 — Build the daily series
`data` already arrives as one spatially-averaged value per day — no clipping
or spatial aggregation happens in this skill.

### Step 2 — Climatology baseline (ts2clm)
`heatwaveR::ts2clm(ts, climatologyPeriod = c("1982-01-01", "2011-12-31"),
                   pctile = 90)`

Builds a day-of-year climatology using the 1982–2011 baseline:
- For each calendar day (1–366), compute the 90th percentile of all observations
  in that day ± 5-day window across the baseline years.
- Output: daily threshold (`thresh`) and seasonal mean (`seas`).

Baseline period is fixed at 1982–2011 per the international MHW definition
(Hobday et al. 2016, Prog. Oceanogr.). Do not change without updating this contract.

### Step 3 — Event detection (detect_event)
`heatwaveR::detect_event(ts, climatology = clim, minDuration = 5, joinAcrossGaps = TRUE)`

A Marine Heatwave event is defined as ≥ 5 consecutive days where SST exceeds the
90th percentile threshold. Parameters:
- `minDuration = 5` — minimum consecutive days above threshold (Hobday et al. 2016)
- `joinAcrossGaps = TRUE` — events separated by ≤ 2 days below threshold are merged
  into a single event

### Step 4 — Annual aggregation
For each calendar year:
- `kpi_mhw_days_per_yr` — total days flagged as MHW (sum of event durations)
- `n_events_per_yr` — number of discrete MHW events
- `mean_intensity_per_yr` — mean peak intensity (°C above threshold) across events

## Random controls
Not applicable — deterministic algorithm. Same input series always produces the
same event detection given fixed parameters.

## Reference value and tolerance
- Reference case: **PENDING** — Cabo Pulmo, baseline period to be defined.
  Expected: low MHW days in pre-2015 period, spike during 2015–2016 El Niño/
  "The Blob" event. Exact values to be verified against published records.
- Tolerance: PENDING (to be set with verified value; expected ± 1 day/yr given
  deterministic algorithm).
- Status: PENDING. Stored in `references/cabo_pulmo_mhw_reference.json`.

## Do-not rules
- Do NOT change the baseline period from 1982–2011 — it is the international
  standard for MHW climatology (Hobday et al. 2016).
- Do NOT change the threshold from the 90th percentile — this is the definition
  of a Marine Heatwave.
- Do NOT change `minDuration` below 5 — events shorter than 5 days do not qualify
  as MHWs under the Hobday definition.
- Do NOT report MHW metrics when the baseline period has < 30 years of data —
  the climatology is unreliable.
- Do NOT compute `bbox_local` inside `skill.R` or at request time — it must
  come from the precomputed lookup table. Adding a new AMP means re-running
  `generate_bbox_lookups.R`, not adding logic here.

## Validation checklist
- [ ] self-consistency: same input → same output across N runs.
- [ ] coherence: zero MHW events in years with consistently low temperatures;
      elevated counts during known El Niño years (2015–2016, 1997–1998).
- [ ] reference: output matches `references/cabo_pulmo_mhw_reference.json`
      within tolerance. PENDING → SKIP with disclosure until verified.

## Success criteria
A complete MHW analysis includes:
- Annual series of `kpi_mhw_days_per_yr` and `n_events_per_yr` for the AMP
  (1982–present).
- Mean intensity per year (°C above threshold).
- Identification of the most intense/longest event on record.

## References
- Hobday, A.J. et al. (2016). A hierarchical approach to defining marine heatwaves.
  Progress in Oceanography, 141, 227–238. https://doi.org/10.1016/j.pocean.2015.12.014
- Schlegel, R.W. & Smit, A.J. (2018). heatwaveR: A central algorithm for the
  detection of heatwaves and cold-spells. Journal of Open Source Software, 3(27), 821.
