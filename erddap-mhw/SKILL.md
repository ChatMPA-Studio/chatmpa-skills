---
name: erddap-mhw
version: 0.1.0
tier: 1
description: >
  Detect and quantify Marine Heatwave (MHW) events at a marine protected area,
  reporting the annual number of heatwave days and events using the heatwaveR
  protocol on daily OISST SST data. Fires on questions about heat stress days,
  marine heatwaves near an AMP, how many days exceeded thermal thresholds, or
  whether heatwave frequency is increasing over time. Companion skill to
  erddap-sst-anomaly — that skill reports mean temperatures; this one reports
  extreme thermal events.
inputs: {}
acquire:
  # Misma fuente que erddap-sst-anomaly pero con serie diaria completa.
  # El orquestador llama al MCP de ERDDAP y manda los datos en el body.
  # Se necesita la serie histórica completa (desde 1982) para construir
  # la climatología de referencia con ts2clm().
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
  - source: payload
    as: geometry_local
    type: sf
# Sin output.table: devuelve un data.frame con la serie anual de MHW metrics.
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

The orchestrator calls the ERDDAP MCP and passes the full daily SST series and
the AMP geometry:

```
get_data(variable="sst", sst_var="sst", bbox=<region>, date_range=["1982-01-01", <today>])
```

- Input `data`: one row per pixel-day:
  - `lat`, `lon` — pixel center coordinates (OISST 0.25° grid, WGS84)
  - `time` — date (daily)
  - `sst` — sea surface temperature (°C)
- `geometry_local` — sf object for the AMP polygon, from `get_amp_geometry()`

The series must start from 1982 — earlier dates are not available in OISST v2.1.
The climatology baseline period (1982–2011) requires at least 30 years of data.

- Missing-data rule: pixel-days with `NA` in `sst` are excluded before any
  aggregation. If coverage for any day < 50% of expected pixels within the polygon,
  that day is excluded from the spatially-averaged series.

## Method (fixed, no degrees of freedom)

### Step 1 — Spatial aggregation
`clip_to_geometry(data, geometry_local)` → daily mean SST within the AMP polygon:
one value per day = `mean(sst)` across all valid pixels inside the geometry.

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
- Do NOT aggregate before Step 1 — the spatial averaging must be done on raw
  pixel-day data, not on annual means.
- Do NOT report MHW metrics when the baseline period has < 20 years of data —
  the climatology is unreliable.

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
- Comparison against the regional trend if geometry_regional is provided.

## References
- Hobday, A.J. et al. (2016). A hierarchical approach to defining marine heatwaves.
  Progress in Oceanography, 141, 227–238. https://doi.org/10.1016/j.pocean.2015.12.014
- Schlegel, R.W. & Smit, A.J. (2018). heatwaveR: A central algorithm for the
  detection of heatwaves and cold-spells. Journal of Open Source Software, 3(27), 821.
