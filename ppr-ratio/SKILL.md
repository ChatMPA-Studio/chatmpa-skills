---
name: ppr-ratio
version: 0.1.0
tier: 1
description: >
  Estimate what fraction of the ocean's primary production is consumed by a
  fishery at a marine protected area, by combining the Primary Production
  Required (PPR) by the fishery with the actual net primary production of the
  AMP. Fires on questions about the ecological footprint of fishing relative to
  ecosystem productivity, whether a fishery is sustainable given local ocean
  conditions, or how fishing pressure scales with primary production across years.
inputs:
  amp_area_km2:
    type: number
    required: true
    description: >
      Area of the AMP polygon in km². Computed by the orchestrator from
      geometry_local via st_area(). Must be a single positive number.
acquire:
  - source: skill_output
    skill: conapesca-ppr
    as: data_ppr
    columns:
      - anio_corte
      - tipo_aviso
      - nombre_cientifico_canonico
      - ppr_kg_c
  - source: skill_output
    skill: erddap-pp
    as: data_pp
    columns:
      - year
      - pp_geomean
      - cobertura_pct
output:
  table: annual
# Fórmula cerrada — determinista. Se comparan las columnas del resultado anual.
comparable_value: [ppr_pct, ppr_total_kg_c, pp_total_kg_c]
reference: references/cabo_pulmo_pprratio_reference.json
validation:
  params:
    amp_area_km2: 71.0  # área marina de Cabo Pulmo NP en km²
depends_on: [conapesca-ppr, erddap-pp]
---

# %PPR — Fraction of Primary Production Required by the Fishery

## Purpose

Answers what fraction of the AMP's net primary production is needed to sustain
the observed catch — a dimensionless pressure index that integrates fishing
demand and ecosystem supply. Values below ~5% are generally considered
sustainable; values above ~25–35% suggest heavy exploitation relative to
local production (Pauly & Christensen 1995).

## Data contract (minimal interface, NOT the local file)

This skill receives outputs from two per-database skills and one spatial
parameter, already prepared by the orchestrator.

- `data_ppr` — `value` from `conapesca-ppr`, filtered to `escala = "local"`:

  | Column | Type | Notes |
  |--------|------|-------|
  | `anio_corte` | int | Reference year |
  | `tipo_aviso` | chr | "MAYORES" or "MENORES" |
  | `nombre_cientifico_canonico` | chr | Canonical scientific name |
  | `ppr_kg_c` | num | PPR in kg C/year |

- `data_pp` — `value` from `erddap-pp`, filtered to `escala = "local"`:

  | Column | Type | Notes |
  |--------|------|-------|
  | `year` | int | Calendar year |
  | `pp_geomean` | num | Annual geometric mean NPP (mgC/m²/day) |
  | `cobertura_pct` | num | Coverage; years with NA pp_geomean are excluded |

- `amp_area_km2` — numeric scalar. Area of the AMP polygon in km².
  Used to convert PP from density (mgC/m²/day) to total production (kg C/year).
  The orchestrator computes this from `geometry_local` via `st_area()`.

- Missing-data rule: join `data_ppr` and `data_pp` on year using complete cases
  only. Years where `pp_geomean` is `NA` (low satellite coverage) are excluded.
  `n_years_used` and `years_excluded` reported in output.

- Aggregation unit: **AMP-year** (one %PPR value per year). Fixed.

## Method (fixed, no degrees of freedom)

### Step 1 — Convert PP to total areal production

```
PP_total_kg_C = pp_geomean (mgC/m²/day) × amp_area_km2 × 1e6 (m²/km²)
                × 365 (days/year) / 1e6 (mg→kg)
              = pp_geomean × amp_area_km2 × 365
```

### Step 2 — Sum PPR across species and fleets per year

```
PPR_total_kg_C = sum(ppr_kg_c)   [over all species × fleets in that year]
```

Also computed per fleet (MAYORES / MENORES) and per species for decomposition.

### Step 3 — Compute %PPR

```
ppr_pct = (PPR_total_kg_C / PP_total_kg_C) × 100
```

**Reference:** Pauly D. & Christensen V. (1995). Primary production required
to sustain global fisheries. *Nature*, 374, 255–257.

## Ecological context (for interpretation only — not thresholds in the code)

Pauly & Christensen (1995) report global %PPR averages by ecosystem type
(Table 2), which serve as reference points:

| Ecosystem type | %PPR (global average, including discards) |
|---|---|
| Open ocean | 1.8% |
| Upwellings | 25.1% |
| Tropical shelves | 24.2% |
| Non-tropical shelves | 35.3% |
| **Coastal / reef systems** | **8.3%** |

Select the ecosystem type that best matches the AMP context. Note that our
calculation excludes discards, so values are not directly comparable with
Pauly & Christensen — ours will be lower for the same fishery. Do NOT present
these as sustainability thresholds; they are ecosystem-level global averages.

## Random controls
Not applicable — deterministic skill (closed-form formula, no resampling).

## Reference value and tolerance
- Reference case: PENDING — %PPR for Cabo Pulmo using *Lutjanus argentiventris*,
  full available time series, to be verified by Edu/Fabio against a direct
  calculation in R.
- Tolerance: ± 0.1 percentage points (rounding only — formula is deterministic).
- Status: PENDING. Stored in `references/cabo_pulmo_pprratio_reference.json`.
  Do NOT fill expected values until human-verified.

## Do-not rules
- Do NOT accept `amp_area_km2 <= 0`.
- Do NOT sum PPR across years — the ratio is computed per year independently.
- Do NOT mix local and regional scale data — `data_ppr` and `data_pp` must
  both be filtered to `escala = "local"` before entering this skill.
- Do NOT interpret %PPR as a causal or mechanistic model — it is a pressure
  index based on steady-state assumptions (Pauly & Christensen 1995).
- Do NOT apply ecological benchmarks as hard thresholds in the code — report
  the value and cite the benchmarks as contextual reference only.
- Do NOT silently drop years with NA — list them in `years_excluded`.

## Validation checklist
- [ ] self-consistency: run N times on fixed data, outputs match exactly
      (deterministic — tolerance = 0).
- [ ] reference: output matches `references/cabo_pulmo_pprratio_reference.json`
      within tolerance. PENDING → SKIP with disclosure until verified.
- [ ] coherence: output declares `formula_used` and `amp_area_km2` matching
      this contract.

## Success criteria

A complete %PPR analysis includes:
- Annual series of `ppr_pct` (total, all species × fleets combined).
- `PPR_total_kg_C` and `PP_total_kg_C` reported per year (allows reader to
  back-calculate and verify the ratio).
- Decomposition by species and fleet: `ppr_kg_c` per
  `anio_corte × tipo_aviso × nombre_cientifico_canonico`.
- `pp_geomean_mgcm2d`, `amp_area_km2`, and `n_years_used` declared in output.
- `years_excluded` listed explicitly (with reason: NA pp_geomean or missing PPR).
- `formula_used` declared in output metadata.
- Ecological interpretation citing the Pauly & Christensen (1995) benchmarks
  as reference, not as absolute thresholds.
