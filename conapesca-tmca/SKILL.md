---
name: conapesca-tmca
description: >
  Computes the Mean Annual Growth Rate (TMCA) of landed volume for a landing
  office (oficina de pesca — administrative unit, not a port) and classifies
  the trend: growing, stable, or declining. Without species filter = overall
  office trend (all species); with species filter = trend of that species or
  resource at that same office. Returns a single numeric value + category string.
---

# CONAPESCA TMCA — Mean Annual Growth Rate

## Purpose

Answers: "Is fishing activity at this office growing or declining?"

Returns a single numeric value (TMCA in %) and a categorical label directly
usable by the chatbot or panel (traffic light / arrow indicator).

**Without species filter:** TMCA reflects the overall trend of the landing office
(all species combined). Valid — CONAPESCA annual reports use TMCA at office and
state level without species breakdown. Note: a *landing office* (oficina de pesca)
is an administrative reporting unit, not a port; one office may cover multiple
landing sites. The chatbot should note this reflects all species at this office.

**With species/resource filter:** TMCA reflects the trend of that species or
resource group *at this specific office*. The MCP already filtered data to the
office before the skill runs — the species filter narrows what is measured, not
where. The result is still office-level, not national.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | data.frame | **Yes** | Pre-aggregated from `get_landings(group_by="year_fleet")`. MCP applies all filters. |
| `window` | integer | No | Years in the window back from the most recent year. Default: 10. Minimum: 2. |
| `fleet_filter` | character or NULL | No | `"MAYORES"`, `"MENORES"`, `"COSECHA"`, or NULL (all fleets). |
| `office_filter` | character or NULL | No | Label only. |
| `state_filter` | character or NULL | No | Label only. |
| `nombre_principal` | character or NULL | No | Label only. Mutually exclusive with `nombre_cientifico_canonico`. |
| `nombre_cientifico_canonico` | character or NULL | No | Label only. |

## Data contract

Columns from `get_landings(group_by="year_fleet")`:

| Column | Type | Description |
|--------|------|-------------|
| `anio_corte` | integer | Year |
| `tipo_aviso` | character | Fleet type: `MAYORES`, `MENORES`, or `COSECHA` |
| `total_kg` | numeric | Sum of landed weight in kg |

Accepted alias: `peso_desembarcado_kg` → `total_kg`.
`total_valor_mxn` is ignored — this skill operates on volume only.

## Method (fixed, no degrees of freedom)

```
1. DATA ALREADY FILTERED BY MCP

2. OPTIONAL FLEET FILTER
   If fleet_filter specified: keep only rows where tipo_aviso = fleet_filter.
   If NULL: aggregate all fleet types.

3. ANNUAL TOTALS
   total_tonnes ← sum(total_kg) / 1000  per anio_corte

4. RESOLVE WINDOW ENDPOINTS
   yr_end   ← max(anio_corte)
   yr_start ← yr_end - window
   If yr_start absent from data: use nearest available year >= yr_start
   with warning(). If none found: use earliest available year.
   n ← yr_end - yr_start  (must be >= 2)

5. TMCA
   TMCA = ((total_tonnes[yr_end] / total_tonnes[yr_start])^(1/n) - 1) × 100

6. CATEGORIZE
   TMCA > +3%          → "growing"
   +1% < TMCA ≤ +3%   → "growing moderately"
   -1% ≤ TMCA ≤ +1%   → "stable"
   -3% ≤ TMCA < -1%   → "declining moderately"
   TMCA < -3%          → "declining"
```

### Notes on TMCA sensitivity

TMCA only uses `yr_start` and `yr_end` — not intermediate years. It is sensitive
to atypical years at either end of the window (e.g., a drought year, an
extraordinary closure). The `value` field returns the full annual series so the
user can assess context.

### Categorization thresholds

Thresholds (±1%, ±3%) are conventional and documented here. They do not represent
an official ecological or regulatory criterion. To adjust, update this section and
the `.THRESH_*` constants in `skill.R`.

## Output structure

```r
list(
  tmca     = <numeric>,    # TMCA in % (2 decimal places). E.g.: 2.34
  category = <character>,  # "growing" | "growing moderately" | "stable" |
                           # "declining moderately" | "declining"
  value    = <data.frame>, # annual series: anio_corte, total_tonnes
  method   = <character>,
  params   = list(window, yr_start, yr_end, n_years, fleet_filter, ...)
)
```

Example chatbot output:
*"Landed volume at the Ensenada office shows a TMCA of +2.3% over the last
10 years (2014–2024), indicating a **moderately growing** trend."*

## Do-not rules
- Do NOT compute TMCA with n < 2 years — raise `stop()`.
- Do NOT interpolate missing years — use the nearest available with `warning()`.
- Do NOT include plots — the value + category is sufficient.
- Do NOT mix `nombre_principal` and `nombre_cientifico_canonico`.

## Validation checklist
- [ ] `tmca` matches manual calculation: `((v_end/v_start)^(1/n)-1)*100`.
- [ ] `category` corresponds to the correct threshold for the `tmca` value.
- [ ] `params$yr_start` and `params$yr_end` both exist in `value$anio_corte`.
- [ ] `warning()` emitted if the ideal start year was unavailable.

## Reference value and tolerance
- Status: PENDING. Do NOT invent one. Store in `references/` when available.

## Success criteria
- Correct numeric `tmca`.
- `category` consistent with documented thresholds.
- `value` with full annual series for context.
