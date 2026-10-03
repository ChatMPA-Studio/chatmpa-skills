---
name: conapesca-tmca
version: 0.1.0
tier: 1
description: >
  Computes the Mean Annual Growth Rate (TMCA) of landed volume for a landing
  office (oficina de pesca — administrative unit, not a port) and classifies
  the trend: growing, stable, or declining. Without species filter = overall
  office trend (all species); with species filter = trend of that species or
  resource at that same office. Returns a single numeric value + category string.
inputs:
  window:
    type: integer
    required: false
    default: 10
    description: >
      Años hacia atrás desde el año más reciente disponible para calcular la
      ventana de la TMCA. Mínimo 2. Si el año ideal de inicio no está
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
acquire:
  # get_landings(group_by="year_fleet") ya trae la serie anual filtrada;
  # el orquestador la manda en el body. office_filter/state_filter/
  # resource_group/species sí se empujan al MCP aquí — a diferencia de
  # conapesca-national-ranking, esta skill necesita UNA sola oficina, no el
  # universo completo. `window` no va a acquire: es un parámetro de cómputo
  # interno de skill.R, no un filtro de datos.
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
    columns:
      - anio_corte
      - tipo_aviso
      - total_kg
output:
  table: value
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
  params: {}
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

| Column | Type | Description |
|--------|------|-------------|
| `anio_corte` | integer | Year |
| `tipo_aviso` | character | Fleet type: `MAYORES`, `MENORES`, or `COSECHA` |
| `total_kg` | numeric | Sum of landed weight in kg |

Accepted alias: `peso_desembarcado_kg` → `total_kg`.
`total_valor_mxn` is ignored — this skill operates on volume only.

## Method (fixed, no degrees of freedom)

```
1. DATA ALREADY FILTERED BY MCP (office, state, resource_group/species)

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
- Do NOT mix `resource_group` and `species`.

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
