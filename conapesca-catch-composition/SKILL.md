---
name: conapesca-catch-composition
version: 0.1.0
tier: 1
description: >
  Shows the production composition of a landing office: percentage from capture
  fisheries (MAYORES + MENORES) vs aquaculture (COSECHA), in both volume and
  estimated value, accumulated over the full available period.
  Two pie charts + composition table.
inputs:
  office_filter:
    type: string
    required: false
    description: >
      Oficina de desembarque (`nombre_oficina`), p. ej. "CABO SAN LUCAS".
      Recomendado acompañar de `state_filter`.
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
      composición incluye todos los recursos.
  species:
    type: string
    required: false
    mutually_exclusive_with: resource_group
    description: >
      Nombre científico canónico (`nombre_cientifico_canonico`), p. ej.
      "Lutjanus peru". No acepta nombres comunes. Mutuamente excluyente con
      `resource_group`.
acquire:
  # Siempre agrega el período completo disponible — no acepta año como input.
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
    columns:
      - anio_corte
      - tipo_aviso
      - total_kg
      - total_valor_mxn
      - n_registros
output:
  table: value
  columns: [component, total_tonnes, total_value_mxn, pct_volume, pct_value, year_min, year_max]
comparable_value: [pct_volume, pct_value]
reference: references/cabo_pulmo_catch_composition_reference.json
validation:
  params: {}
depends_on: []
---

# CONAPESCA Catch Composition — Capture vs Aquaculture

## Purpose

Answers: "What share of this office's production comes from fishing vs aquaculture?"

Aggregates the full available period and expresses composition as percentages.
Does not repeat time series — that is `conapesca-landings-timeseries`.

## Data contract (minimal interface, NOT the local file)

Columns from `get_landings(group_by="year_fleet")`:

| Column | Type | Description |
|--------|------|-------------|
| `anio_corte` | integer | Year |
| `tipo_aviso` | character | Fleet type: `MAYORES`, `MENORES`, or `COSECHA` |
| `total_kg` | numeric | Sum of landed weight in kg |
| `total_valor_mxn` | numeric | Sum of estimated value (MXN) |
| `n_registros` | integer | Record count |

Accepted aliases: `peso_desembarcado_kg` → `total_kg`, `valor_pesos_estimado` → `total_valor_mxn`,
`n_records` → `n_registros`.

## Method (fixed, no degrees of freedom)

```
1. DATA ALREADY FILTERED BY MCP (office, state, resource_group/species)

2. AGGREGATE FULL PERIOD
   capture_kg    ← sum(total_kg)        where tipo_aviso IN ('MAYORES','MENORES')
   aquac_kg      ← sum(total_kg)        where tipo_aviso = 'COSECHA'
   capture_valor ← sum(total_valor_mxn) where tipo_aviso IN ('MAYORES','MENORES')
   aquac_valor   ← sum(total_valor_mxn) where tipo_aviso = 'COSECHA'

3. COMPUTE PERCENTAGES
   pct_volume ← capture_kg    / (capture_kg    + aquac_kg)    × 100
   pct_value  ← capture_valor / (capture_valor + aquac_valor) × 100
```

## Output structure

**`value`** — two-row composition table:
```
component | total_tonnes | total_value_mxn | pct_volume | pct_value | year_min | year_max
```
Rows: `"Capture"` and `"Aquaculture"`.

**`plot_volumen`** — pie chart of volume composition (%).
**`plot_valor`** — pie chart of value composition (%).

### Plot specifications
- Two segments: Capture (`#4E79A7`) and Aquaculture (`#59A14F`).
- Labels inside each segment: percentage with 1 decimal. Omitted if < 2%.
- Legend horizontal at bottom: "Capture (MAYORES + MENORES)" | "Aquaculture (COSECHA)".
- No chart title — handled by the dashboard panel.
- Subtitle: `filter_label | period` (e.g., `"All resources | 2014–2024"`).

## Do-not rules
- Do NOT show absolute values in pie charts — percentages only.
- Do NOT filter or re-aggregate `data` — the MCP already filtered.
- Do NOT include TMCA — that is the independent skill `conapesca-tmca`.
- Do NOT mix `resource_group` and `species`.

## Validation checklist
- [ ] `pct_volume[Capture] + pct_volume[Aquaculture]` = 100.
- [ ] `pct_value[Capture] + pct_value[Aquaculture]` = 100 (may differ ±0.1 due to rounding).
- [ ] `total_tonnes[Capture] + total_tonnes[Aquaculture]` = period total.

## Reference value and tolerance
- Status: PENDING. Do NOT invent one. Store in `references/` when available.

## Success criteria
- Table with two rows and correct percentages.
- Two pie charts with visible percentages and clear legend.
