---
name: conapesca-catch-composition
version: 0.3.0
tier: 1
description: >
  Shows the production composition of a landing office: percentage from capture
  fisheries (MAYORES + MENORES) vs aquaculture (COSECHA), in both volume and
  estimated value, accumulated over the requested period (year_from–year_to)
  or the full available period if no years are given.
  Composition table, plus two pie charts when ggplot2 is installed.
description_es:
  - >
    Muestra la composición de la producción de una oficina de desembarque:
    qué porcentaje viene de la pesca de captura (embarcaciones mayores y
    menores) y qué porcentaje de la acuacultura (avisos de cosecha), en
    volumen y en valor estimado, acumulado en el periodo solicitado. Se activa
    con preguntas sobre cuánto de la producción de una oficina es captura y
    cuánto acuacultura.
  - qué parte del volumen o del valor de una oficina de pesca viene de la captura y qué parte de la acuacultura.
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
  year_from:
    type: integer
    required: false
    description: >
      Año inicial del periodo (inclusive). Si se omiten year_from y year_to,
      se usa todo el periodo disponible.
  year_to:
    type: integer
    required: false
    description: >
      Año final del periodo (inclusive). Si se omiten year_from y year_to,
      se usa todo el periodo disponible.
acquire:
  # Agrega el periodo year_from–year_to (o todo el periodo disponible si se omiten).
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
      - n_records
output:
  columns: [component, total_tonnes, total_value_mxn, pct_volume, pct_value, year_min, year_max]
comparable_value: [pct_volume, pct_value]
reference: references/cabo_pulmo_catch_composition_reference.json
validation:
  params:
    office_filter: CABO SAN LUCAS
    state_filter: BAJA CALIFORNIA SUR
    year_from: 2016
    year_to: 2025
depends_on: []
---

# CONAPESCA Catch Composition — Capture vs Aquaculture

## Purpose

Answers: "What share of this office's production comes from fishing vs aquaculture?"

Aggregates the requested period (`year_from`–`year_to`, or the full available
period if omitted) and expresses composition as percentages.
Does not repeat time series — that is `conapesca-landings-timeseries`.

## Data contract (minimal interface, NOT the local file)

Columns from `get_landings(group_by="year_fleet")`:

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `anio_corte` | integer | year | Year |
| `tipo_aviso` | character | — | Fleet type: `MAYORES`, `MENORES`, or `COSECHA` |
| `total_kg` | numeric | kg | Sum of landed weight |
| `total_valor_mxn` | numeric | MXN (nominal) | Sum of estimated value |
| `n_records` | integer | records | Number of landing records |

Accepted aliases: `peso_desembarcado_kg` → `total_kg`, `valor_pesos_estimado` → `total_valor_mxn`.
`n_records` (name delivered by the MCP) is renamed internally to `n_registros`.

- **Missing data:** sums use `na.rm = TRUE`. If capture + aquaculture is 0 (volume
  or value), the corresponding percentages are NA with a warning().
- Any `tipo_aviso` other than MAYORES, MENORES or COSECHA is ignored (the curated
  base has none).
- **Aggregation unit:** the whole period received, by component (Capture / Aquaculture).
- **Data source:** Comisión Nacional de Acuacultura y Pesca [CONAPESCA] (2026). Data
  curated by the ChatMPA team (pipeline `conapesca-database`: cleaning and species
  catalogue) from the delivery of 29 June 2026.

## Method (fixed, no degrees of freedom)

```
1. DATA ALREADY FILTERED BY MCP (office, state, resource_group/species, year_from/year_to)

2. AGGREGATE FULL PERIOD
   capture_kg    ← sum(total_kg)        where tipo_aviso IN ('MAYORES','MENORES')
   aquac_kg      ← sum(total_kg)        where tipo_aviso = 'COSECHA'
   capture_valor ← sum(total_valor_mxn) where tipo_aviso IN ('MAYORES','MENORES')
   aquac_valor   ← sum(total_valor_mxn) where tipo_aviso = 'COSECHA'

3. COMPUTE PERCENTAGES
   pct_volume ← capture_kg    / (capture_kg    + aquac_kg)    × 100
   pct_value  ← capture_valor / (capture_valor + aquac_valor) × 100
```

`pct_volume` and `pct_value` are rounded to 1 decimal.

## Random controls
Not applicable (deterministic skill).

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
- [ ] Self-consistency, reference and coherence checks (validation harness, `run_checks.R`).

## Reference value and tolerance
- Case: Cabo San Lucas landing office (BCS), all species, 2016–2025 (proxy for the
  Cabo Pulmo MPA: the skill resolves by landing office).
- Expected value: `pct_volume` = 100.0 and `pct_value` = 100.0 (Capture), verified by
  Carolina (2026-09-30). Trivial case: the office has no COSECHA.
- Tolerance: ±0.05 (the skill rounds to 1 decimal).
- Seed: not applicable.
- Status: VERIFIED. Cases in `references/cabo_pulmo_catch_composition_reference.json`.
- Second case (non-trivial, with aquaculture): La Paz landing office (BCS), all
  species, 2016–2025, `pct_volume` and `pct_value` of Capture. Status: PENDING until
  verified by an independent calculation
  (`Validación ChatMPA/referencias_conapesca/verificacion_la_paz_composicion.R`,
  outside the repos).

## Success criteria
- Table with two rows and correct percentages.
- Two pie charts with visible percentages and clear legend.

## References
- Comisión Nacional de Acuacultura y Pesca. (2026). *Avisos de arribo y de cosecha*
  [Datos sin publicar, obtenidos mediante solicitud de acceso a la información pública
  núm. 340008100012626, Plataforma Nacional de Transparencia; entregados el 29 de junio
  de 2026].
