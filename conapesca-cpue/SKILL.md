---
name: conapesca-cpue
version: 0.2.2
tier: 1
description: >
  Compute CPUE (catch per unit effort) as a historical time series for a
  landing office, disaggregated by fleet type (MAYORES / MENORES). Fires on
  dashboard panel requests for a specific office, optionally filtered by
  resource group (nombre_principal) or species (nombre_cientifico_canonico).
description_es:
  - >
    Calcula la serie histórica de CPUE (captura por unidad de esfuerzo) de
    una oficina de desembarque, desagregada por tipo de flota
    (mayores/menores). Se activa con preguntas sobre el panel de captura o
    esfuerzo pesquero de una oficina específica, opcionalmente filtradas por
    grupo de recurso o especie.
  - esfuerzo pesquero o captura por unidad de esfuerzo de una oficina de desembarque.
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
    type: array
    items: integer
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
        species:        nombre_cientifico_canonico
        resource_group: nombre_principal
        state_filter:   estado
        office_filter:  oficina
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
      # nombre_principal y nombre_cientifico_canonico NO están en el output de
      # get_landings(group_by="folio"): una fila por viaje. El filtro de
      # especie/recurso se aplica server-side vía params (chatmpa-skills#16).
output:
  columns: [anio_corte, tipo_aviso, cpue_media, cpue_sd, n_viajes, n_viajes_excluidos, peso_desembarcado_kg_total, n_viajes_recomputado]
  scalars:
    kpi_cpue_menores: numeric  # mean(cpue_media) for MENORES over the filtered year range; NA if no rows
    kpi_cpue_mayores: numeric  # mean(cpue_media) for MAYORES over the filtered year range; NA if no rows
# Skill determinista (sin controles aleatorios), así que las corridas deben
# coincidir exactamente. Se comparan las dos columnas calculadas: `cpue_media`
# sola dejaría pasar un cambio que solo afecte la dispersión.
comparable_value: [cpue_media, cpue_sd]
reference: references/cabo_pulmo_cpue_reference.json
# Con qué corre el ARNÉS contra el fixture. `state_filter` y `office_filter`
# son obligatorios en toda llamada real.
validation:
  params:
    species: Balistes polylepis
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
| `peso_desembarcado_kg` | numeric | Landed weight in kg of the trip (only the requested species/resource when a filter is set) |
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

**Data source:** Comisión Nacional de Acuacultura y Pesca [CONAPESCA] (2026). Data
curated by the ChatMPA team (pipeline `conapesca-database`: cleaning and species
catalogue) from the delivery of 29 June 2026.

## Method (fixed, no degrees of freedom)

CPUE is computed as **mean of ratios** (not ratio of means) to treat each trip
as an independent observation and avoid large trips dominating the index.

The CPUE is nominal (not standardized): it does not correct for changes in fishing
power, in the spatial distribution of the fleet or in vessel composition, so it is
not always proportional to abundance (Gulland, 1971). Each row of
`get_landings(group_by = "folio")` is one trip. `cpue_media` and `cpue_sd` are
rounded to 4 decimals.

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

5. KPI SCALARS
   Computed from cpue_series after step 3, over all years present in the output
   (year_range filtering already applied by run_skill() itself in step 1 — not
   by the MCP; species/resource/state/office filters are the only ones pushed
   down to the get_landings() call):
   kpi_cpue_menores ← mean(cpue_media[tipo_aviso == "MENORES"], na.rm = TRUE)
   kpi_cpue_mayores ← mean(cpue_media[tipo_aviso == "MAYORES"], na.rm = TRUE)
   If a fleet has no rows in cpue_series, its KPI = NA.
```

### Interpretation
Computed per fleet (MENORES / MAYORES) on the annual `cpue_media` series:
- Before/after comparison (`before_after()`): first 5 years vs. last 5 years.
- Mann-Kendall monotonic trend test (Mann, 1945; Kendall, 1975) via `mk_trend()`
  (`Kendall::MannKendall`, `shared/interpretation/interpret.R`); minimum number of
  years as set in `mk_trend()`.
- In this skill Mann-Kendall only feeds `interpretation$significance` and the
  insight sentence; it does not decide the status, which is always `"ambiguous"`
  (declining CPUE may reflect overfishing, stock depletion or reduced effort).

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
- Colors: MAYORES = `#4E79A7` (blue), MENORES = `#F28E2B` (orange) — Tableau 10
  palette, consistent with the other conapesca skills (e.g. landings-timeseries).
- Point shapes: MAYORES = filled triangle (▲), MENORES = filled circle (●).
  Points with `n_viajes < 5` are rendered as a hollow circle (○) for both fleets
  to signal low reliability — the shape is not fleet-specific for unreliable points.
- Labels: real `cpue_media` value printed above each point (below hollow points).
- Legend: horizontal, below the chart.
- Caption: notes hollow-point threshold, log scale if applied, method used.

## Random controls
Not applicable (deterministic skill).

## Reference value and tolerance
- Reference cases: 4 (`cpue_media` and `cpue_sd` for MAYORES 2018 and MENORES 2020)
  in `references/cabo_pulmo_cpue_reference.json`.
- Case: *Balistes polylepis*, Cabo San Lucas landing office (BCS), full series (proxy
  for the Cabo Pulmo MPA: the skill resolves by landing office). Year chosen per
  fleet: MAYORES with ≥ 5 trips, MENORES with ≥ 30 trips.
- Expected values: 231.3858 / 54.2755 (MAYORES 2018) and 247.4857 / 383.7774
  (MENORES 2020), verified by Carolina (2026-09-30).
- Tolerance: ±0.00005 (the skill rounds to 4 decimals).
- Seed: not applicable.
- Status: VERIFIED.

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
- Do NOT compute `kpi_cpue_*` in the frontend — the skill returns them as scalars
  over the already-filtered year range.

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
- `kpi_cpue_menores` and `kpi_cpue_mayores` present in output (NA if fleet absent).


## References
- Comisión Nacional de Acuacultura y Pesca. (2026). *Avisos de arribo y de cosecha*
  [Datos sin publicar, obtenidos mediante solicitud de acceso a la información pública
  núm. 340008100012626, Plataforma Nacional de Transparencia; entregados el 29 de junio
  de 2026].
- Gulland, J. A. (1971). *Manual de métodos para la evaluación de las poblaciones de
  peces. Parte 1. Análisis de poblaciones de peces* (Manuales de la FAO de Ciencias
  Pesqueras, FRs/M4). Editorial Acribia; FAO. https://www.fao.org/4/x5685s/x5685s00.htm
- Kendall, M. G. (1975). *Rank correlation methods* (4th ed.). Charles Griffin.
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica, 13*(3),
  245–259. https://doi.org/10.2307/1907187
- McLeod, A. I. (2025). *Kendall: Kendall rank correlation and Mann-Kendall trend test*
  (Version 2.2.2) [R package]. https://CRAN.R-project.org/package=Kendall

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
