---
name: conapesca-landings-timeseries
version: 0.1.0
tier: 1
description: >
  Produce historical annual time series of landed volume (tonnes) and estimated
  production value (MXN) for a landing office, disaggregated by fleet type
  (TOTAL, MAYORES, MENORES, COSECHA). Fires on dashboard panel requests for
  volume or value trends for a specific office, optionally filtered by resource
  or species.
inputs:
  office_filter:
    type: string
    required: false
    description: >
      Oficina de desembarque (`nombre_oficina`), p. ej. "CABO SAN LUCAS". Es
      la unidad de análisis. Recomendado acompañar de `state_filter`.
  state_filter:
    type: string
    required: false
    description: >
      Estado de la oficina de desembarque (`nombre_estado`). Recomendado
      junto con `office_filter` — los nombres de oficina se repiten entre
      estados.
  resource_group:
    type: string
    required: false
    mutually_exclusive_with: species
    description: >
      Grupo/recurso pesquero (`nombre_principal`), p. ej. "PARGO", "JUREL".
      Mutuamente excluyente con `species`. Si ninguno se proporciona, la
      serie incluye todos los recursos.
  species:
    type: string
    required: false
    mutually_exclusive_with: resource_group
    description: >
      Nombre científico canónico (`nombre_cientifico_canonico`), p. ej.
      "Lutjanus peru". No acepta nombres comunes. Mutuamente excluyente con
      `resource_group`.
  year_from:
    type: integer
    required: false
    description: >
      Año inicial del rango (inclusive). Si se omite junto con `year_to`, se
      usa la serie completa disponible.
  year_to:
    type: integer
    required: false
    description: >
      Año final del rango (inclusive).
  include_cpue:
    type: boolean
    required: false
    default: false
    description: >
      Si es true, el orquestador debe además adquirir `data_folio` (vía
      `get_landings(group_by="folio")`) para que la skill compute la serie de
      CPUE internamente usando `conapesca-cpue`. Si es false u omitido,
      `data_folio` no se adquiere y `value_cpue`/`plot_cpue` salen `NULL`.
acquire:
  - source: payload
    as: data
    provider:
      server: conapesca
      tool: get_landings
      args:
        group_by: year_fleet
      params:
        office_filter:  oficina
        state_filter:   estado
        resource_group: nombre_principal
        species:        nombre_cientifico_canonico
        year_from:      year_from
        year_to:        year_to
    columns:
      - anio_corte
      - tipo_aviso
      - total_kg
      - total_valor_mxn
      - n_registros
  - source: payload
    as: data_folio
    required: false
    # Solo se adquiere cuando include_cpue=true. Mismos filtros que `data`
    # salvo year_from/year_to: conapesca-cpue filtra año internamente en R
    # (ver su SKILL.md), así que aquí se trae la serie folio completa.
    provider:
      server: conapesca
      tool: get_landings
      args:
        group_by: folio
      params:
        office_filter:  oficina
        state_filter:   estado
        resource_group: nombre_principal
        species:        nombre_cientifico_canonico
    columns:
      - folio_aviso
      - anio_corte
      - tipo_aviso
      - nombre_estado
      - nombre_oficina
      - peso_desembarcado_kg
      - dias_efectivos
      - dias_efectivos_fuente
      - flag_fecha_generica
      - flag_dias_efectivos_sospechoso
      - flag_periodo_futuro
output:
  scalars:
    kpi_vol_total:   numeric
    kpi_vol_mayores: numeric
    kpi_vol_menores: numeric
    kpi_vol_cosecha: numeric
    kpi_val_total:   numeric
    kpi_val_mayores: numeric
    kpi_val_menores: numeric
    kpi_val_cosecha: numeric
# Skill determinista. Se comparan los KPIs de TOTAL en volumen y valor — un
# cambio que afecte la agregación por flota (MAYORES/MENORES/COSECHA) se
# reflejaría en TOTAL de todos modos, y son los dos campos que resumen ambas
# tablas (value_volumen, value_valor).
comparable_value: [kpi_vol_total, kpi_val_total]
reference: references/cabo_pulmo_landings_timeseries_reference.json
validation:
  params: {}
depends_on: []
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

When `include_cpue=true`, the orchestrator provides folio-level data from
`get_landings(group_by="folio")`. See `conapesca-cpue/SKILL.md` for its
required columns and quality filters. `conapesca-cpue`'s `run_skill()` filters
by year internally (a single `year_range = c(start, end)` argument) — this
skill reconstructs that vector from `year_from`/`year_to` before the internal
call, so `data_folio` itself is fetched without a year restriction.

## Method (fixed, no degrees of freedom)

```
1. DATA ALREADY FILTERED BY MCP
   office, state, resource_group/species, year_from/year_to were applied in
   get_landings() for `data`. `data_folio` (when present) is filtered by
   office/state/resource_group/species only — year is applied later, inside
   the embedded conapesca-cpue call.

2. COMPUTE TOTAL SERIES
   For each anio_corte: sum(total_kg), sum(total_valor_mxn) across all tipo_aviso
   tipo_aviso = "TOTAL", n_registros = sum of all fleets

3. COMBINE
   Bind TOTAL rows + fleet rows.
   Factor order: TOTAL, MAYORES, MENORES, COSECHA.

4. DERIVE TONNES
   total_toneladas ← total_kg / 1000

5. KPI SCALARS
   Computed from the combined table (after step 3) for each fleet in
   c("TOTAL", "MAYORES", "MENORES", "COSECHA"):
     kpi_vol_{tolower(fleet)} ← mean(total_toneladas[tipo_aviso == fleet], na.rm = TRUE)
     kpi_val_{tolower(fleet)} ← mean(total_valor_mxn[tipo_aviso == fleet], na.rm = TRUE)
   Result: 8 scalar fields. NA if a fleet has no rows for the office/filter.

6. CPUE (when data_folio provided)
   Reconstruct year_range <- c(year_from, year_to) (using -Inf/Inf for any
   side left NULL). source conapesca-cpue/skill.R in isolated env
   (new.env()). call run_skill(data=data_folio, office_filter, state_filter,
   resource_group, species, year_range) in panel mode. attach value_cpue and
   plot_cpue to output.
```

### Output structure

**Tabular (`value_volumen` and `value_valor`):** same structure, different metric column.
```
anio_corte | tipo_aviso | total_toneladas | total_valor_mxn | n_registros
```
Both tables are returned in `list(value_volumen, value_valor)` — they share the
same rows but the frontend uses different columns for each panel.

**Scalars (`kpi_vol_*`, `kpi_val_*`):** 8 pre-computed KPI scalars, one per fleet
per metric, over all years present in `data` (year_from/year_to already filtered
by the MCP). NA if a fleet has no rows for the office/filter combination.

| Field             | Fleet   | Metric             | Unit    |
|-------------------|---------|--------------------|---------|
| `kpi_vol_total`   | TOTAL   | mean annual volume | tonnes  |
| `kpi_vol_mayores` | MAYORES | mean annual volume | tonnes  |
| `kpi_vol_menores` | MENORES | mean annual volume | tonnes  |
| `kpi_vol_cosecha` | COSECHA | mean annual volume | tonnes  |
| `kpi_val_total`   | TOTAL   | mean annual value  | MXN     |
| `kpi_val_mayores` | MAYORES | mean annual value  | MXN     |
| `kpi_val_menores` | MENORES | mean annual value  | MXN     |
| `kpi_val_cosecha` | COSECHA | mean annual value  | MXN     |

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
- Do NOT mix `resource_group` and `species` — mutually exclusive.
- Do NOT sum `valor_pesos_estimado` across NA records — `.normalize_ts_cols()` renames
  the column; the TOTAL sum uses `na.rm = TRUE`.
- Do NOT call CPUE from `data` — always pass `data_folio` separately for folio-level data.
- Do NOT pass `year_range` to the embedded `conapesca-cpue` call without
  reconstructing it from `year_from`/`year_to` first — CPUE's own contract
  still uses a single vector, not two scalars.
- Do NOT compute `kpi_vol_*` / `kpi_val_*` in the frontend — the skill returns
  them as scalars over the already-filtered year range.

## Validation checklist
- [ ] self-consistency: run twice on fixed data, outputs match.
- [ ] TOTAL = sum of MAYORES + MENORES + COSECHA for each year (volume and value).
- [ ] Volume in tonnes (not kg) in both table and plot.
- [ ] Four series present in output (or fewer if a fleet type has no data for the office).
- [ ] `resource_group` and `species` never both non-NULL.
- [ ] `value_cpue` and `plot_cpue` are NULL when `data_folio` is not provided.

## Success criteria
- Two data tables (volume, value) with all four fleet series per year.
- Two plots, one per metric, with four labeled trend lines.
- Years with n < 5 records shown as hollow points in the plot.
- When `data_folio` provided: `value_cpue` and `plot_cpue` populated from conapesca-cpue.
- 8 KPI scalars present (`kpi_vol_*`, `kpi_val_*`), NA where fleet is absent.
