# DHW Methodology and Interpretation

## Introduction

This reference describes the NOAA Coral Reef Watch (CRW) thermal stress
methodology used in this skill: the HotSpot, the Maximum Monthly Mean (MMM)
climatology, accumulation into Degree Heating Weeks (DHW), the operational
alert levels, and how to interpret the results. The formulas and snippets here
are consistent with the inline `calculate_hotspot` / `calculate_dhw` functions
in `SKILL.md`.

## The Components

### Maximum Monthly Mean (MMM) climatology

The MMM is the warmest of the twelve long-term monthly mean SST values at a
location. It represents the upper bound of the normal annual temperature cycle
that corals are adapted to. It is computed from a multi-year SST climatology
(CRW uses a fixed reference climatology); the warmest monthly climatological
value is selected per grid cell.

```python
# Long-term monthly climatology, then take the warmest month per cell
monthly_clim = ds['sst_celsius'].groupby('time.month').mean('time')
mmm = monthly_clim.max('month')   # MMM per grid cell
```

### HotSpot (HS) — instantaneous stress

The HotSpot is the positive anomaly of SST above the MMM. Only warming above
the historical seasonal maximum counts; values at or below the MMM are set to
zero.

```
HotSpot = max(SST - MMM, 0)
```

```python
hotspot = (ds['sst_celsius'] - mmm).clip(min=0)
```

### Degree Heating Weeks (DHW) — accumulated stress

DHW accumulates HotSpots over a **rolling 12-week (84-day) window**. Following
the CRW convention, only HotSpots **≥ 1 °C** contribute to accumulation
(weaker positive anomalies are treated as biologically insignificant). The sum
is expressed in **°C-weeks**.

```
DHW = (1/7) * Σ over the last 84 days of [ HotSpot where HotSpot >= 1 ]
```

The division by 7 converts a sum of daily °C values into °C-weeks. For data
already at weekly resolution, sum the qualifying HotSpots over the most recent
12 observations instead.

```python
# Daily SST input (consistent with SKILL.md calculate_dhw)
hs_significant = hotspot.where(hotspot >= 1, 0)
dhw = hs_significant.rolling(time=84, center=False).sum() / 7
```

## Coral Reef Watch Alert Levels

CRW maps the combination of HotSpot presence and DHW magnitude onto a set of
operational stress levels:

| Alert Level         | Condition                          | Meaning                              |
|---------------------|------------------------------------|--------------------------------------|
| No Stress           | HotSpot ≤ 0                        | SST at or below MMM                  |
| Bleaching Watch     | 0 < HotSpot < 1                    | SST above MMM but below 1 °C         |
| Bleaching Warning   | HotSpot ≥ 1 and 0 < DHW < 4        | Stress accumulating                  |
| Alert Level 1       | HotSpot ≥ 1 and 4 ≤ DHW < 8        | Significant bleaching likely         |
| Alert Level 2       | HotSpot ≥ 1 and DHW ≥ 8            | Severe bleaching + mortality likely  |

```python
import xarray as xr

def crw_alert_level(hotspot, dhw):
    """Classify each cell/timestep into the CRW alert level (0-4)."""
    level = xr.zeros_like(dhw)                       # 0 = No Stress
    level = level.where(~(hotspot > 0), 1)           # 1 = Watch
    level = level.where(~((hotspot >= 1) & (dhw > 0)), 2)   # 2 = Warning
    level = level.where(~((hotspot >= 1) & (dhw >= 4)), 3)  # 3 = Alert 1
    level = level.where(~((hotspot >= 1) & (dhw >= 8)), 4)  # 4 = Alert 2
    return level
```

## Interpretation Thresholds

The two DHW thresholds below are the widely cited ecological benchmarks:

| DHW (°C-weeks) | Expected coral response                                |
|----------------|--------------------------------------------------------|
| **≥ 4**        | Significant coral bleaching becomes likely             |
| **≥ 8**        | Severe, widespread bleaching and significant mortality |

These describe **likelihood and severity**, not certainty. Realized bleaching
depends on local conditions and the susceptibility of the coral community.

## Caveats and Good Practice

- **Climatology consistency.** DHW values are only comparable when computed
  against the same MMM/reference climatology. Mixing an ad-hoc MMM derived from
  a short record with the official CRW product yields non-comparable numbers.
- **Temporal resolution.** The `/7` conversion assumes daily input. Weekly or
  composite products require summing over the equivalent 12-week window rather
  than 84 daily samples; check the time step before applying the rolling sum.
- **Window edges.** The first 84 days (or 12 weeks) of a series have an
  incomplete window and will be NaN with `rolling(...).sum()`. Do not interpret
  these as zero stress.
- **Spatial resolution.** Coarse SST products (e.g. 0.25°) smooth over reef-scale
  thermal refugia and microhabitats; fine-scale bleaching can occur where the
  gridded DHW looks moderate.
- **Cloud gaps and SST source.** Infrared SST is degraded by cloud cover and
  represents a thin skin layer; gaps and sensor differences can bias HotSpot and
  DHW. Prefer gap-filled, validated products for operational stress monitoring.
- **Acclimatization and other stressors.** DHW captures thermal dose only. It
  does not account for prior thermal history, light, water quality, or disease,
  all of which modulate the actual bleaching outcome.

## See Also

- `SKILL.md` — inline `calculate_hotspot` and `calculate_dhw` functions.
- `references/mapping_templates.md` — DHW alert map styling.
- NOAA Coral Reef Watch: https://coralreefwatch.noaa.gov/
