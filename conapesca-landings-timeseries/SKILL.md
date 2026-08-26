---
name: conapesca-landings-timeseries
description: >
  Produce historical annual time series of landed volume (tonnes) and estimated
  production value (MXN) for a landing office, disaggregated by fleet type
  (TOTAL, MAYORES, MENORES, COSECHA). Fires on dashboard panel requests for
  volume or value trends for a specific office, optionally filtered by resource
  or species.
---

# CONAPESCA Landings Timeseries — Historic Volume and Porduction Value per office

## Purpose
Produces two time series for a specific landing office:
1. **Volume**: annual landed weight in tonnes, by fleet type.
2. **Value**: annual estimated production value (MXN), by fleet type.

Both series are disaggregated into four lines: TOTAL, MAYORES, MENORES, COSECHA.
TOTAL = MAYORES + MENORES + COSECHA (consistent with CONAPESCA annual reports).
The skill always returns all four series; the frontend decides which to display
based on the user's fleet filter.

## Parameters (required at call time)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | data.frame | **Yes** | Pre-aggregated from `get_landings(group_by="year_fleet")`. MCP handles all filtering. |
| `data_folio` | data.frame or NULL | No | Folio-level data from `get_landings(group_by="folio")`. When provided, CPUE is computed internally via `conapesca-cpue`. |
| `office_filter` | character or NULL | No | Label only — filtering already done by MCP. |
| `state_filter` | character or NULL | No | Label only — filtering already done by MCP. |
| `nombre_principal` | character or NULL | No | Label only. NULL = all resources. Mutually exclusive with `nombre_cientifico_canonico`. |
| `nombre_cientifico_canonico` | character or NULL | No | Label only. NULL = all species. Mutually exclusive with `nombre_principal`. |
| `year_range` | integer vector or NULL | No | Label only. |

**Mutual exclusion rule:** `nombre_principal` and `nombre_cientifico_canonico`
cannot both be non-NULL. The frontend resolves which filter applies before calling the MCP.

## Data contract (minimal interface, NOT the local file)

### `data` — pre-aggregated year_fleet format

Input columns from `get_landings(group_by="year_fleet")`:

| Column | Type | Description |
|--------|------|-------------|
| `anio_corte` | integer | Landing year |
| `tipo_aviso` | character | Fleet type: `MAYORES`, `MENORES`, or `COSECHA` |
| `total_kg` | numeric | Sum of landed weight in kg (MCP alias: `peso_desembarcado_kg`) |
| `total_valor_mxn` | numeric | Sum of estimated value in MXN (MCP alias: `valor_pesos_estimado`) |
| `n_registros` | integer | Record count (MCP alias: `n_records`) |

Column name aliases are handled transparently by `.normalize_ts_cols()`.
No quality flag filtering is applied — all records contribute to the sums.

### `data_folio` — optional folio-level format

When CPUE is requested, provide folio-level data from `get_landings(group_by="folio")`.
See `conapesca-cpue/SKILL.md` for its required columns and quality filters.

## Method (fixed, no degrees of freedom)

```
1. DATA ALREADY FILTERED BY MCP
   All filtering (office, state, species, year_range) was applied in get_landings().

2. COMPUTE TOTAL SERIES
   For each anio_corte: sum(total_kg), sum(total_valor_mxn) across all tipo_aviso
   tipo_aviso = "TOTAL", n_registros = sum of all fleets

3. COMBINE
   Bind TOTAL rows + fleet rows.
   Factor order: TOTAL, MAYORES, MENORES, COSECHA.

4. DERIVE TONNES
   total_toneladas ← total_kg / 1000

5. CPUE (when data_folio provided)
   source conapesca-cpue/skill.R in isolated env (new.env())
   call run_skill(data=data_folio, office_filter, ...) in panel mode
   attach value_cpue and plot_cpue to output
```

### Output structure

**Tabular (`value_volumen` and `value_valor`):** same structure, different metric column.
```
anio_corte | tipo_aviso | total_toneladas | total_valor_mxn | n_registros
```
Both tables are returned in `list(value_volumen, value_valor)` — they share the
same rows but the frontend uses different columns for each panel.

**Visual (`plot_volumen`, `plot_valor`):** two ggplot2 trend line charts.

### Plot specifications (both charts)
- X axis: year (`anio_corte`)
- Y axis: auto-scaled for readability — see scale rules below.
- Four lines: TOTAL, MAYORES, MENORES, COSECHA (Tableau 10, first 4 colors).
- Point shapes: TOTAL = square (■), MAYORES = triangle (▲), MENORES = circle (●),
  COSECHA = diamond (◆). All filled for n ≥ 5 records; hollow for n < 5.
- Labels: value above each point (in display units, matching the axis scale).
- Legend: horizontal, below the chart. Includes hollow-point note "n < 5 registros".
- No chart title (handled by the dashboard panel).

### Y-axis scale rules
**Volume:** always in tonnes (kg / 1000). Log10 applied if max/min > 10.
**Value:** auto-scaled to keep axis labels readable:
  - max ≥ 1 billion → display in billions (`"Miles de millones MXN"`)
  - max ≥ 1 million → display in millions (`"Millones MXN"`)
  - max ≥ 1 thousand → display in thousands (`"Miles MXN"`)
  - otherwise → display as MXN
  Log10 applied if max/min ratio > 10 (after scaling).

Labels on points always show the value in display units (same scale as axis).

## Random controls
Not applicable (deterministic skill).

## Reference value and tolerance
- Status: PENDING. Do NOT invent one. Store in `references/` when available.

## Do-not rules
- Do NOT filter or aggregate `data` inside this skill — MCP already did it.
- Do NOT apply quality flag filters to volume/value — totals are not effort-normalized.
- Do NOT mix `nombre_principal` and `nombre_cientifico_canonico` — mutually exclusive.
- Do NOT sum `valor_pesos_estimado` across NA records — `.normalize_ts_cols()` renames
  the column; the TOTAL sum uses `na.rm = TRUE`.
- Do NOT call CPUE from `data` — always pass `data_folio` separately for folio-level data.

## Validation checklist
- [ ] self-consistency: run twice on fixed data, outputs match.
- [ ] TOTAL = sum of MAYORES + MENORES + COSECHA for each year (volume and value).
- [ ] Volume in tonnes (not kg) in both table and plot.
- [ ] Four series present in output (or fewer if a fleet type has no data for the office).
- [ ] `nombre_principal` and `nombre_cientifico_canonico` never both non-NULL.
- [ ] `value_cpue` and `plot_cpue` are NULL when `data_folio` is not provided.

## Success criteria
- Two data tables (volume, value) with all four fleet series per year.
- Two plots, one per metric, with four labeled trend lines.
- Years with n < 5 records shown as hollow points in the plot.
- When `data_folio` provided: `value_cpue` and `plot_cpue` populated from conapesca-cpue.
