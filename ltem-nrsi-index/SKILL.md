---
name: ltem-nrsi-index
version: 0.1.0
tier: 2
description: >
  Assess the trophic health of a reef and answer whether it is healthy,
  degraded, or recovering, from the LTEM database. Fires on questions about
  reef trophic balance, apex-predator recovery, overfishing signatures, or
  "is this reef healthy" — by computing the Normalized Reef State Index (NRSI)
  from the relative biomass of upper, lower, and consumer trophic levels.
inputs:
  n_boot:
    type: integer
    required: false
    default: 100
    description: >
      Bootstrap resamples for 95% CI computation. Range 100–500. Seed is
      fixed at 42 — CIs are reproducible regardless of n_boot value.
acquire:
  - source: payload
    as: data
    provider:
      server: ltem
      tool: get_nrsi_data
    columns:
      - time
      - value
      - TrophicLevelF
      - transect
      - reef
output:
  table: nrsi_by_reef
  columns: [time, reef, nrsi, ci_lo_95, ci_hi_95, ci_includes_zero, health_category, n_transects, n_ltl_dominant]
# Bootstrap con seed=42 — determinista. Se comparan NRSI y CIs por reef-year.
comparable_value: [nrsi, ci_lo_95, ci_hi_95]
reference: references/cabo_pulmo_nrsi_reference.json
validation:
  params:
    n_boot: 100
depends_on: []
---

# LTEM Normalized Reef State Index (NRSI)

## Purpose
Answers whether a reef is trophically healthy, degraded, or recovering by
computing the Normalized Reef State Index (NRSI) — the relative biomass balance
of upper, lower, and consumer trophic levels — per reef, with uncertainty and
regional comparison.

## Data contract (minimal interface, NOT the local file)
- Input: a table on the minimal contract carrying, per observation:
  - `time` — survey year,
  - `value` — `Biomass` in g/m², and
  - the categorical trophic-level range `TrophicLevelF` (e.g. `2-2.5`, `4-4.5`)
  - a transect identifier and a reef identifier for aggregation.
  `lat`/`lon` apply when NRSI is mapped spatially. The skill reads this
  interface, not a file with a fixed name.
- Trophic mapping (fixed):
  - `2-2.5` → LTL (Lower Trophic Level: herbivores, detritivores)
  - `4-4.5` → UTL (Upper Trophic Level: apex predators)
  - all other levels (`2.5-3`, `3-3.5`, `3.5-4`) → CTL (Consumer Trophic Level)
- Missing-data rule: transects where UTL=LTL=CTL=0 (no fish recorded) are
  **excluded** from the reef average with a warning. Never emit a silent NaN.
  Implemented in `skill.R`: rows with `total_biomass == 0` are dropped before
  NRSI computation; count reported as `n_empty` in the warning message.
- Aggregation unit: **transect** for NRSI computation, then averaged to
  **reef-year**. Fixed, not optional.

## Method (fixed, no degrees of freedom)
Relative biomass proportions UTL, LTL, CTL are computed **within each transect**
(each category's summed biomass / total), then:

```
Standard:     NRSI = (UTL + LTL - CTL) / (UTL + LTL + CTL)
Conditional:  if LTL > UTL + CTL,  NRSI = UTL / (UTL + CTL)
```

The conditional prevents artificially high NRSI when herbivore/detritivore
biomass (LTL) dominates the system. NRSI is computed per transect, then averaged
per reef.

Computation steps: classify each observation's `TrophicLevelF` → sum biomass per
transect per category → compute relative proportions → apply standard or
conditional formula per transect → average transect NRSI per reef.

- Reference: NRSI formula follows the LTEM analysis approach
  (`04-full_trends_analysis.R`, lines 1038–1075); bootstrap adapted from
  `resample_mean()` in the same script. See `references/nrsi_methodology.md`.
- Parameters (documented defaults): bootstrap `n_boot = 100` (range 100–500);
  95% CI from the 2.5th and 97.5th percentiles of the bootstrap distribution.

## Random controls
- Seed: **fixed at `42`** (`set.seed(42L)` called once before the bootstrap
  loop in `skill.R`). CIs are fully reproducible across runs.
- Bootstrap: resample transect-level NRSI values within each reef, with
  replacement (n = number of transects per reef), `n_boot = 100` by default.

## Reference value and tolerance
- Reference case: **PENDING** — Cabo Pulmo (year to be defined) → expected NRSI
  value. Cabo Pulmo typically shows positive NRSI (apex-predator recovery), but
  the exact expected number is not yet hand-verified.
- Tolerance: PENDING (to be set with the reference value).
- Status: PENDING: needs a value verified by Edu/Fabio. Do NOT invent one.
  Stored in `references/` with `status: PENDING`.

## Do-not rules
- Do NOT emit a silent NaN for the UTL=LTL=CTL=0 edge case (transect with no
  fish). Exclude from the reef average with a warning — implemented in `skill.R`.
- Do NOT run the bootstrap without a fixed seed — CIs would not be reproducible
  across runs. Seed is fixed at `42` in `skill.R`.
- Do NOT report NRSI as a confident assessment when the bootstrap 95% CI
  includes 0 — the reef's trophic state is ambiguous; say so.
- Do NOT let LTL dominance inflate NRSI — apply the conditional rule, do not
  use the standard formula when LTL > UTL + CTL.

## Validation checklist
- [ ] self-consistency: run N times on fixed data, outputs match within tolerance.
- [ ] reference: output matches the references/ value within tolerance.
- [ ] coherence: the output uses the methods this contract specifies.

### Resolved fixes (implemented in `skill.R`)
- [x] Seed fixed at `42` (`set.seed(42L)`) — bootstrap CIs are reproducible.
- [x] UTL=LTL=CTL=0 edge case: transects with zero total biomass are excluded
      with a `warning()` before NRSI computation; count reported in message.
- [x] Reference case created: `references/cabo_pulmo_nrsi_reference.json`
      with `status: PENDING` — awaiting human-verified values from Edu/Fabio.

## Success criteria
A complete NRSI analysis includes:
- Regional comparison with a statistical test (Kruskal-Wallis across regions).
- Per-reef NRSI for at least one region, with highest/lowest reefs identified.
- Bootstrap 95% confidence intervals for key reefs (flag CIs that include 0).
- Temporal comparison if multiple years are available.
- A clear mapping of NRSI values to ecological health categories:
  0.5–1.0 Excellent · 0.0–0.5 Good · -0.5–0.0 Degraded · -1.0–-0.5 Severely degraded.
