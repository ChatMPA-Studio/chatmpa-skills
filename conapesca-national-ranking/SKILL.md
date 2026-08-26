---
name: conapesca-national-ranking
description: >
  Computes the national position of a landing office by total landed volume
  (tonnes) and estimated production value (MXN). Without species filter:
  overall port importance. With species filter: position within that fishery.
  Returns ranking scalars and a full ranked table. No plots.
---

# CONAPESCA National Ranking — National position of a landing office

## Purpose

Answers: "Where does this office rank nationally?"

**Without species filter:** ranks the office by total landed volume/value vs all
other offices in the country — reflects the administrative importance of the
office as a reporting unit. Note: a *landing office* (oficina de pesca) is an
administrative entity, not a port. One office may cover multiple landing sites,
and one port may fall under different offices depending on the state.

**With species filter:** ranks the office within that specific fishery (e.g.,
"rank 3 of 45 offices for abalone").

Both uses are valid and complementary.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | data.frame | **Yes** | Pre-aggregated from `get_landings(group_by="office_year_fleet")`. MCP applies all filters. Covers ALL offices. |
| `office_filter` | character | **Yes** | Focal office (`nombre_oficina`). |
| `state_filter` | character | **Yes** | Focal office state. Required — office names are not unique across states. |
| `nombre_principal` | character or NULL | No | Label only. Mutually exclusive with `nombre_cientifico_canonico`. |
| `nombre_cientifico_canonico` | character or NULL | No | Label only. |
| `year_range` | integer vector or NULL | No | Label only. |
| `fleet_filter` | character or NULL | No | `"MAYORES"`, `"MENORES"`, `"COSECHA"`, or NULL (all fleets). |

## Data contract

Columns from `get_landings(group_by="office_year_fleet")`:

| Column | Type | Description |
|--------|------|-------------|
| `nombre_oficina` | character | Office name |
| `nombre_estado` | character | State name |
| `anio_corte` | integer | Year |
| `tipo_aviso` | character | Fleet type: `MAYORES`, `MENORES`, or `COSECHA` |
| `total_kg` | numeric | Sum of landed weight in kg |
| `total_valor_mxn` | numeric | Sum of estimated value (MXN) |
| `n_registros` | integer | Record count |

Accepted aliases: `peso_desembarcado_kg` → `total_kg`, `valor_pesos_estimado` → `total_valor_mxn`,
`n_records` → `n_registros`.

## Method (fixed, no degrees of freedom)

```
1. DATA ALREADY FILTERED BY MCP

2. OPTIONAL FLEET FILTER
   If fleet_filter specified: keep only rows where tipo_aviso = fleet_filter.
   If NULL: aggregate all fleet types.

3. AGGREGATE PER OFFICE (sum across all years and fleets)
   total_tonnes    ← sum(total_kg) / 1000
   total_valor_mxn ← sum(total_valor_mxn)
   n_years         ← count of distinct anio_corte
   n_registros     ← sum(n_registros)

4. RANK
   rank_volumen ← rank(-total_tonnes,    ties.method = "min")
   rank_valor   ← rank(-total_valor_mxn, ties.method = "min")
   n_offices    ← nrow(value)

5. NATIONAL SHARE
   pct_volumen ← total_tonnes_focal    / sum(total_tonnes)    × 100
   pct_valor   ← total_valor_mxn_focal / sum(total_valor_mxn) × 100

6. EXTRACT FOCAL SCALARS
   Identify focal office by nombre_oficina + nombre_estado (never name alone).
```

## Output structure

### `ranking` — focal office scalars
```r
list(
  rank_volumen    = <integer>,  # volume rank (1 = highest)
  rank_valor      = <integer>,  # value rank
  n_offices       = <integer>,  # total offices in universe
  pct_volumen     = <numeric>,  # % of national total volume
  pct_valor       = <numeric>,  # % of national total value
  total_toneladas = <numeric>,  # accumulated volume of focal office (t)
  total_valor_mxn = <numeric>   # accumulated value of focal office (MXN)
)
```

Example chatbot output: *"Ensenada ranks 3rd out of 127 offices by landed
volume, accounting for 4.2% of the national total."*

### `value` — full ranked table
```
nombre_oficina | nombre_estado | total_toneladas | total_valor_mxn |
rank_volumen   | rank_valor    | pct_volumen | pct_valor | n_years | n_registros
```
Sorted by `rank_volumen` ascending. No plots — visualization is handled by the
frontend/chatbot using this table if additional context is requested.

## Do-not rules
- Do NOT produce plots — the frontend/chatbot handles visualization.
- Do NOT identify the focal office by `nombre_oficina` alone — always use
  `nombre_oficina + nombre_estado` to avoid false matches across states.
- Do NOT mix `nombre_principal` and `nombre_cientifico_canonico`.
- Do NOT include CPUE ranking — deferred pending pre-computation strategy.

## Validation checklist
- [ ] `sum(value$pct_volumen)` ≈ 100 (may differ slightly due to rounding).
- [ ] `rank_volumen = 1` corresponds to the office with the highest `total_toneladas`.
- [ ] Focal office present in `value` with correct scalars in `ranking`.
- [ ] `n_offices = nrow(value)`.

## Reference value and tolerance
- Status: PENDING. Do NOT invent one. Store in `references/` when available.

## Success criteria
- `ranking` with 7 correct scalars for the focal office.
- `value` with all offices ranked, sorted by `rank_volumen`.
