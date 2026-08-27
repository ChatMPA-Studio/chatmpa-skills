---
name: conapesca-cpue
version: 0.1.0
tier: 1
description: >
  Compute CPUE (catch per unit effort) as a historical time series for a
  landing office, disaggregated by fleet type (MAYORES / MENORES). Fires on
  dashboard panel requests for a specific office, optionally filtered by
  resource group (nombre_principal) or species (nombre_cientifico_canonico).
inputs:
  species:
    type: string
    required: false
    mutually_exclusive_with: resource_group
    description: >
      Nombre científico canónico (`nombre_cientifico_canonico`), p. ej.
      "Lutjanus peru". No acepta nombres comunes: "pargo" debe resolverse
      antes de llegar acá. Mutuamente excluyente con `resource_group`.
      Si ninguno se proporciona, se computa CPUE para todas las especies.
  resource_group:
    type: string
    required: false
    mutually_exclusive_with: species
    description: >
      Grupo/recurso pesquero (`nombre_principal`), p. ej. "PARGO", "JUREL".
      Mutuamente excluyente con `species`. Si ninguno se proporciona, se
      computa CPUE para todas las especies.
  state_filter:
    type: string
    required: true
    description: >
      Estado de la oficina de desembarque (`nombre_estado`), p. ej.
      "BAJA CALIFORNIA SUR". Requerido únicamente para desambiguar nombres
      de oficina que se repiten entre estados (p. ej. EL ROSARIO existe en
      Baja California y en Sinaloa). No define escala de análisis.
  office_filter:
    type: string
    required: true
    description: >
      Oficina de desembarque (`nombre_oficina`), p. ej. "CABO SAN LUCAS".
      Es la unidad de análisis. Siempre debe acompañarse de `state_filter`.
  year_range:
    type: integer_vector
    required: false
    description: >
      Two-element vector `[start, end]`, e.g. `[2010, 2020]`. If omitted,
      the full available time series is returned.
acquire:
  # El MCP de CONAPESCA ya devuelve este contrato completo y sin tope de filas
  # vía get_landings(group_by="folio"), así que el orquestador trae la tabla y
  # la manda en el body. No hay razón para que el servicio la baje de nuevo.
  - source: payload
    as: data
    provider:
      server: conapesca
      tool: get_landings
      args:
        group_by: folio
      params:
        species:        especie
        resource_group: nombre_principal
        state_filter:   estado
        office_filter:  oficina
    columns:
      - folio_aviso
      - anio_corte
      - tipo_aviso
      - nombre_estado
      - nombre_oficina
      - nombre_principal
      - nombre_cientifico_canonico
      - peso_desembarcado_kg
      - dias_efectivos
      - dias_efectivos_fuente
      - flag_fecha_generica
      - flag_dias_efectivos_sospechoso
      - flag_periodo_futuro
# Sin `output.table`: run_skill() devuelve un solo data.frame, no una lista de
# tablas, y ahí no hay nada que elegir.
#
# Skill determinista (sin controles aleatorios), así que las corridas deben
# coincidir exactamente. Se comparan las dos columnas calculadas: `cpue_media`
# sola dejaría pasar un cambio que solo afecte la dispersión.
comparable_value: [cpue_media, cpue_sd]
reference: references/cabo_pulmo_cpue_reference.json
# Con qué corre el ARNÉS contra el fixture. `state_filter` y `office_filter`
# son obligatorios en toda llamada real.
validation:
  params:
    species: Lutjanus peru
    state_filter: BAJA CALIFORNIA SUR
    office_filter: CABO SAN LUCAS
depends_on: []
---

# CONAPESCA CPUE — Serie histórica por oficina

## Purpose
Produces a CPUE time series (kg per effective fishing day) for a specific
landing office, disaggregated by fleet type. CPUE is computed as mean-of-ratios
across folios (fishing trips). Used as the CPUE panel in the ChatMPA dashboard
and as a fishing-pressure proxy in AMP analyses.

The skill always returns MAYORES and MENORES as separate series. The frontend
decides which series to render based on the fleet filter selected by the user.
COSECHA is always excluded — there is no effort concept in aquaculture.

## Parameters (required at call time)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `office_filter` | character | **Yes** | Landing office name (`nombre_oficina`). The office is the unit of analysis. |
| `state_filter` | character | **Yes** | State name (`nombre_estado`). Required — office names are not unique across states. |
| `nombre_principal` | character or NULL | No | Resource group filter (`nombre_principal`, e.g. `"JUREL"`). NULL = all resources. Mutually exclusive with `nombre_cientifico_canonico`. |
| `nombre_cientifico_canonico` | character or NULL | No | Species filter (`nombre_cientifico_canonico`, e.g. `"Seriola lalandi"`). NULL = all species. Mutually exclusive with `nombre_principal`. |
| `year_range` | integer vector or NULL | No | Two-element vector `c(start, end)`. NULL = full available range. |

**Mutual exclusion rule:** `nombre_principal` and `nombre_cientifico_canonico`
cannot both be non-NULL. The frontend resolves which filter the user selected
(resource dropdown vs species dropdown) before calling the skill.

### Suggested office mapping for MVP AMPs
```
Cabo Pulmo          → office: CABO SAN LUCAS  · state: BAJA CALIFORNIA SUR
Loreto              → office: LORETO           · state: BAJA CALIFORNIA SUR
Isla Espíritu Santo → office: LA PAZ           · state: BAJA CALIFORNIA SUR
```

## Data contract (minimal interface, NOT the local file)

Input columns required from the CONAPESCA MCP (`get_landings(group_by="folio")`):

| Column | Type | Description |
|--------|------|-------------|
| `folio_aviso` | character | Trip/notice identifier (aggregation unit) |
| `anio_corte` | integer | Landing year |
| `tipo_aviso` | character | Fleet type: `MAYORES` or `MENORES` |
| `nombre_estado` | character | State of the landing office |
| `nombre_oficina` | character | Landing office |
| `nombre_principal` | character | Resource group (e.g. JUREL, OSTION) |
| `nombre_cientifico_canonico` | character | Canonical species name |
| `peso_desembarcado_kg` | numeric | Landed weight in kg |
| `dias_efectivos` | integer | Effective fishing days (quality-controlled) |
| `dias_efectivos_fuente` | character | Source of effort value: `original`, `duracion`, `recomputado` |
| `flag_fecha_generica` | logical | TRUE = generic date placeholder; effort unreliable |
| `flag_dias_efectivos_sospechoso` | logical | TRUE = `dias_efectivos` likely from generic dates |
| `flag_periodo_futuro` | logical | TRUE = a period date is after `fecha_aviso`; informational only |

**Missing-data rules:**
- Records with `flag_fecha_generica = TRUE`, `flag_dias_efectivos_sospechoso = TRUE`,
  or `is.na(dias_efectivos)` are **excluded** from CPUE computation.
- Records with `flag_periodo_futuro = TRUE` are **included** (effort may still be valid).
- Records with `dias_efectivos_fuente = "recomputado"` are **included** but counted
  separately in `n_viajes_recomputado` — effort was recovered from date fields, not
  directly captured.
- If a folio has zero `peso_desembarcado_kg` after species/resource filtering, it
  is excluded (target resource not landed on that trip).

**Fleet scope:**
- Include: `MAYORES`, `MENORES`.
- Exclude: `COSECHA` — aquaculture production, no effort concept.
- MAYORES and MENORES always computed and reported **separately**. Their CPUEs are
  not comparable (different vessel size, effort scale, reporting unit).

**Aggregation unit:** `folio_aviso` (one fishing trip / notice). Fixed, not optional.

## Method (fixed, no degrees of freedom)

CPUE is computed as **mean of ratios** (not ratio of means) to treat each trip
as an independent observation and avoid large trips dominating the index.

### Step-by-step

```
1. FILTER
   nombre_estado  = <state_filter>
   AND nombre_oficina = <office_filter>
   AND tipo_aviso IN ('MAYORES', 'MENORES')
   AND flag_fecha_generica            = FALSE
   AND flag_dias_efectivos_sospechoso = FALSE
   AND NOT is.na(dias_efectivos)
   AND peso_desembarcado_kg           > 0
   [AND nombre_principal              = <nombre_principal>]       ← if provided
   [AND nombre_cientifico_canonico    = <nombre_cientifico_canonico>] ← if provided
   [AND anio_corte BETWEEN year_range[1] AND year_range[2]]      ← if provided

2. AGGREGATE BY FOLIO
   For each folio_aviso:
     catch_folio  ← sum(peso_desembarcado_kg)
     effort_folio ← dias_efectivos               [folio-level, do NOT sum]
     cpue_folio   ← catch_folio / effort_folio   [kg / day]

3. AGGREGATE BY YEAR × FLEET
   Group by: anio_corte, tipo_aviso
   cpue_media ← mean(cpue_folio)
   cpue_sd    ← sd(cpue_folio)
   n_viajes   ← count of folios included

4. COUNT EXCLUDED TRIPS (for transparency)
   n_viajes_excluidos ← folios matching state + office + fleet + species/resource
                        filters but removed by quality flags in step 1.
```

### Output structure

**Tabular (`value`):**
```
anio_corte | tipo_aviso | cpue_media | cpue_sd | n_viajes | n_viajes_excluidos |
peso_desembarcado_kg_total | n_viajes_recomputado
```
- `peso_desembarcado_kg_total`: total landed weight for context (not normalized)
- `n_viajes_recomputado`: trips where `dias_efectivos_fuente = "recomputado"`

**Visual (`plot`):** ggplot2 trend line chart — always generated alongside the table.
- X axis: year (`anio_corte`)
- Y axis: `cpue_media` (kg / effective fishing day). Log₁₀ scale applied automatically
  when max/min ratio across all series exceeds 10 (large fleet-size differences).
- Two lines: one per fleet type (MAYORES / MENORES), always in the same panel.
- Colors: MAYORES = `#E69F00` (amber), MENORES = `#0072B2` (blue) — Okabe-Ito palette,
  colorblind-friendly.
- Point shapes: MAYORES = filled triangle (▲), MENORES = filled circle (●).
  Points with `n_viajes < 5` rendered as hollow shapes (△ / ○) to signal low reliability.
- Labels: real `cpue_media` value printed above each point (below hollow points).
- Legend: horizontal, below the chart.
- Caption: notes hollow-point threshold, log scale if applied, method used.

## Random controls
Not applicable (deterministic skill).

## Reference value and tolerance
- Reference case: PENDING — needs an office + species/resource + year combination
  with a hand-verified CPUE value.
- Tolerance: PENDING.
- Status: PENDING. Do NOT invent one. Store in `references/` with `status: PENDING`.

## Do-not rules
- Do NOT sum `dias_efectivos` across species rows of the same folio — effort is
  already at folio level. Summing produces inflated denominators.
- Do NOT mix MAYORES and MENORES into a single CPUE series — their effort units
  are not comparable.
- Do NOT include COSECHA records — they represent aquaculture production, not
  fishing effort.
- Do NOT use records with `flag_fecha_generica = TRUE` even if `dias_efectivos`
  looks reasonable — both effort and duration fields are unreliable.
- Do NOT run `office_filter` without `state_filter` — office names are not unique
  across states (e.g. EL ROSARIO exists in Baja California and Sinaloa).
- Do NOT pass both `nombre_principal` and `nombre_cientifico_canonico` as non-NULL
  simultaneously — the frontend must resolve which filter applies before calling.
- Do NOT report a CPUE series with fewer than 5 trips per year-fleet cell without
  flagging it explicitly — small n makes the mean unreliable.
- Do NOT interpret CPUE by office as spatially precise — landing offices record
  where fish were landed, not where they were caught.

## Validation checklist
- [ ] self-consistency: run twice on fixed data, outputs match exactly.
- [ ] reference: output matches the `references/` value within tolerance.
- [ ] coherence: mean-of-ratios formula used, not ratio-of-means.
- [ ] MAYORES and MENORES reported separately in all outputs.
- [ ] `n_viajes_excluidos` is present and non-zero for real data.
- [ ] No COSECHA records in filtered input.
- [ ] `office_filter` never used without `state_filter`.
- [ ] `nombre_principal` and `nombre_cientifico_canonico` never both non-NULL.

## Success criteria
A complete CPUE panel output must include:
- CPUE time series (MAYORES + MENORES separate) for the target office.
- `n_viajes` and `n_viajes_excluidos` reported per year-fleet cell.
- Years with n < 5 trips flagged in the narrative.
- If no especie/resource filter: note that series represents all landings for the office.

---

## Planned scale architecture — PENDING: gradilla costera + base limpia

> Este bloque documenta la arquitectura objetivo del MVP. No modifica el
> contrato actual. Implementar cuando la gradilla y los puertos de desembarque
> georreferenciados estén disponibles.

### Cambio de escala local
- **Actual**: `office_filter` (nombre_oficina) como unidad de análisis
- **Planeado**: sitios de desembarque georreferenciados asociados a celdas de
  la gradilla donde `nombre_amp == <amp_name>`
- Requiere: puertos de desembarque limpios y georreferenciados en los folios CONAPESCA

### Cambio de escala regional (para contexto AMP)
- **Actual**: no aplica en el panel
- **Planeado**: `region_id` de `conapesca-lfo-regions` — región de manejo pesquero
- Mecánica: folios se asignan a región vía `nombre_oficina` → lookup de lfo-regions

### Lo que NO cambia
- Fórmula CPUE: mean-of-ratios por folio — idéntica
- Separación MAYORES/MENORES
- Reglas de exclusión por flags de calidad

### Dependencias para implementar
- [ ] Gradilla costera disponible (sf con `nombre_amp`, `region_id`, `nombre_oficina`)
- [ ] Puertos de desembarque georreferenciados en la base CONAPESCA
- [ ] `conapesca-lfo-regions` ejecutado (lookup oficina → region_id)
