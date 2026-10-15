---
name: conapesca-tmca
version: 0.2.2
tier: 1
description: >
  Computes the Mean Annual Growth Rate (TMCA) of landed volume for a landing
  office (oficina de pesca — administrative unit, not a port) and classifies
  the trend: growing, stable, or declining. Without species filter = overall
  office trend (all species); with species filter = trend of that species or
  resource at that same office. Returns a single numeric value + category string.
description_es:
  - >
    Calcula la tasa media de crecimiento anual (TMCA) del volumen desembarcado
    en una oficina de desembarque y clasifica la tendencia como creciente,
    estable o decreciente. Sin filtro, es la tendencia de toda la oficina; con
    filtro de recurso o especie, la de esa pesquería en la misma oficina. Se
    activa con preguntas sobre si los desembarques de una oficina están
    creciendo o disminuyendo.
  - si los desembarques de una oficina de pesca están creciendo, estables o disminuyendo, y a qué tasa anual.
inputs:
  window:
    type: integer
    required: false
    default: 10
    description: >
      Años hacia atrás desde `year_to` (o desde el año más reciente disponible
      si se omite) para calcular la ventana de la TMCA. Mínimo 2. Si el año ideal de inicio no está
      disponible, se usa el más cercano posterior, con warning.
  fleet_filter:
    type: string
    required: false
    description: >
      Tipo de flota (`tipo_aviso`): "MAYORES", "MENORES", "COSECHA". Si se
      omite, se agregan todas las flotas.
  office_filter:
    type: string
    required: false
    description: >
      Oficina de desembarque (`nombre_oficina`), p. ej. "ENSENADA". Opcional:
      si se omite, la TMCA refleja el agregado nacional (o el universo que el
      resto de filtros delimite). Se recomienda acompañar de `state_filter`
      cuando se especifica, ya que los nombres de oficina se repiten entre
      estados.
  state_filter:
    type: string
    required: false
    description: >
      Estado de la oficina de desembarque (`nombre_estado`). Recomendado junto
      con `office_filter` para desambiguar oficinas homónimas entre estados.
  resource_group:
    type: string
    required: false
    mutually_exclusive_with: species
    description: >
      Grupo/recurso pesquero (`nombre_principal`), p. ej. "PARGO", "JUREL".
      Mutuamente excluyente con `species`. Si ninguno se proporciona, la TMCA
      refleja todas las especies combinadas en la oficina.
  species:
    type: string
    required: false
    mutually_exclusive_with: resource_group
    description: >
      Nombre científico canónico (`nombre_cientifico_canonico`), p. ej.
      "Lutjanus peru". No acepta nombres comunes. Mutuamente excluyente con
      `resource_group`.
  year_to:
    type: integer
    required: false
    description: >
      Año final de la ventana (inclusive). Debe ser un año completo: el
      orquestador manda el menor entre el año elegido por el usuario y el
      último año completo de la entrega vigente (valor de configuración que se
      actualiza con cada entrega; con la entrega del 29 de junio de 2026 es
      2025, porque 2026 sólo llega al 31 de mayo). Si se omite, se usa el
      último año disponible.
acquire:
  # get_landings(group_by="year_fleet") ya trae la serie anual filtrada;
  # el orquestador la manda en el body. office_filter/state_filter/
  # resource_group/species sí se empujan al MCP aquí — a diferencia de
  # conapesca-national-ranking, esta skill necesita UNA sola oficina, no el
  # universo completo. `window` no va a acquire: es un parámetro de cómputo
  # interno de skill.R, no un filtro de datos. `year_to` sí se manda: fija el
  # último año de la serie (yr_end).
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
        fleet_filter:   tipo_aviso
        year_to:        year_to
    columns:
      - anio_corte
      - tipo_aviso
      - total_kg
output:
  columns: [anio_corte, total_tonnes]
  scalars:
    tmca:     numeric    # TMCA en %, 2 decimales
    category: character  # "growing" | "growing moderately" | "stable" | "declining moderately" | "declining"
# category se deriva determinísticamente de tmca (función escalón) — comparar
# solo tmca basta para detectar cualquier desviación en el cálculo o la
# categorización.
comparable_value: [tmca]
reference: references/cabo_pulmo_tmca_reference.json
validation:
  params:
    office_filter: CABO SAN LUCAS
    state_filter: BAJA CALIFORNIA SUR
    window: 10
    year_to: 2025
depends_on: []
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

## Data contract (minimal interface, NOT the local file)

Input columns required from the CONAPESCA MCP (`get_landings(group_by="year_fleet")`):

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `anio_corte` | integer | year | Year |
| `tipo_aviso` | character | — | Fleet type: `MAYORES`, `MENORES`, or `COSECHA` |
| `total_kg` | numeric | kg | Sum of landed weight (converted to `total_tonnes`, t) |

Accepted alias: `peso_desembarcado_kg` → `total_kg`.
`total_valor_mxn` is ignored — this skill operates on volume only.

- **Aggregation unit:** annual total, summing MAYORES, MENORES and COSECHA (or only
  `fleet_filter` if given).
- **Missing data:** sums use `na.rm = TRUE`; if the ideal start year is missing, the
  nearest later year is used (step 4).
- **Incomplete years:** the TMCA always ends in the last complete year (`year_to`).
  A partial year (e.g. 2026, January–May in the current delivery) biases the TMCA
  of every office towards decline, so it is never used as `yr_end`.
- **Data source:** Comisión Nacional de Acuacultura y Pesca [CONAPESCA] (2026). Data
  curated by the ChatMPA team (pipeline `conapesca-database`: cleaning and species
  catalogue) from the delivery of 29 June 2026.

## Method (fixed, no degrees of freedom)

```
1. DATA ALREADY FILTERED BY MCP (office, state, resource_group/species, year_to)

2. OPTIONAL FLEET FILTER
   If fleet_filter specified: keep only rows where tipo_aviso = fleet_filter.
   If NULL: aggregate all fleet types.

3. ANNUAL TOTALS
   total_tonnes ← sum(total_kg) / 1000  per anio_corte

4. RESOLVE WINDOW ENDPOINTS
   yr_end   ← max(anio_corte)   (= year_to when given)
   yr_start ← yr_end - window
   If yr_start absent from data: use nearest available year >= yr_start
   with warning(). If none found: use earliest available year.
   n ← yr_end - yr_start  (must be >= 2)

5. TMCA
   TMCA = ((total_tonnes[yr_end] / total_tonnes[yr_start])^(1/n) - 1) × 100
   rounded to 2 decimals.
   If total_tonnes[yr_start] = 0: TMCA undefined → stop().
   If total_tonnes[yr_end] = 0: TMCA = -100 (a collapse to zero is a valid result).

6. CATEGORIZE (on the TMCA already rounded to 2 decimals)
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

## Random controls
Not applicable (deterministic skill).

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
- Do NOT end the window in an incomplete year — `year_to` is the last complete year.
- Do NOT interpolate missing years — use the nearest available with `warning()`.
- Do NOT include plots — the value + category is sufficient.
- Do NOT mix `resource_group` and `species`.

## Validation checklist
- [ ] `tmca` matches manual calculation: `((v_end/v_start)^(1/n)-1)*100`.
- [ ] `category` corresponds to the correct threshold for the `tmca` value.
- [ ] `params$yr_start` and `params$yr_end` both exist in `value$anio_corte`.
- [ ] `warning()` emitted if the ideal start year was unavailable.
- [ ] Self-consistency, reference and coherence checks (validation harness, `run_checks.R`).

## Reference value and tolerance
- Reference cases: 1 (`tmca`) in `references/cabo_pulmo_tmca_reference.json`.
- Case: Cabo San Lucas landing office (BCS), all species and fleets, `window` = 10,
  `year_to` = 2025 (2015 vs 2025; proxy for the Cabo Pulmo MPA: the skill resolves by
  landing office).
- Expected value: −20.43 (% per year), verified by Carolina (2026-10-01).
- Tolerance: ±0.005 (the skill rounds to 2 decimals).
- Seed: not applicable.
- Status: VERIFIED.

## Success criteria
- Correct numeric `tmca`.
- `category` consistent with documented thresholds.
- `value` with full annual series for context.

## References
- Comisión Nacional de Acuacultura y Pesca. (2026). *Avisos de arribo y de cosecha*
  [Datos sin publicar, obtenidos mediante solicitud de acceso a la información pública
  núm. 340008100012626, Plataforma Nacional de Transparencia; entregados el 29 de junio
  de 2026].

The categorization thresholds (±1 %, ±3 %) are an internal convention without a
bibliographic source (see *Categorization thresholds*).
