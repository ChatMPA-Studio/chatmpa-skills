---
name: conapesca-national-ranking
version: 0.2.0
tier: 1
description: >
  Computes the national position of a landing office by total landed volume
  (tonnes) and estimated production value (MXN). Without species filter:
  overall port importance. With species filter: position within that fishery.
  Returns ranking scalars and a full ranked table. No plots.
inputs:
  office_filter:
    type: string
    required: true
    description: >
      Oficina de desembarque focal (`nombre_oficina`), p. ej. "ENSENADA". Es
      la unidad que se rankea. Siempre debe acompañarse de `state_filter`.
  state_filter:
    type: string
    required: true
    description: >
      Estado de la oficina focal (`nombre_estado`). Requerido — los nombres
      de oficina no son únicos entre estados.
  resource_group:
    type: string
    required: false
    mutually_exclusive_with: species
    description: >
      Grupo/recurso pesquero (`nombre_principal`), p. ej. "PARGO", "JUREL".
      Mutuamente excluyente con `species`. Si ninguno se proporciona, el
      ranking es por volumen/valor total de todas las especies.
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
  fleet_filter:
    type: string
    required: false
    description: >
      Tipo de flota (`tipo_aviso`): "MAYORES", "MENORES", "COSECHA". Si se
      omite, se agregan todas las flotas.
acquire:
  # get_landings(group_by="office_year_fleet") trae TODAS las oficinas que
  # cumplan el resto de filtros — es el universo contra el que se rankea.
  # office_filter y state_filter NO se mandan al MCP: identificar la oficina
  # focal es responsabilidad del Method (paso 6), dentro de la tabla ya traída.
  # Si se mandaran, la tool devolvería sólo esa oficina (o ese estado) y no
  # habría universo nacional contra el cual rankear.
  - source: payload
    as: data
    provider:
      server: conapesca
      tool: get_landings
      args:
        group_by: office_year_fleet
      params:
        resource_group: nombre_principal
        species:        nombre_cientifico_canonico
        fleet_filter:   tipo_aviso
        year_from:      year_from
        year_to:        year_to
    columns:
      - nombre_oficina
      - nombre_estado
      - anio_corte
      - tipo_aviso
      - total_kg
      - total_valor_mxn
      - n_records
output:
  table: value
  columns: [nombre_oficina, nombre_estado, total_toneladas, total_valor_mxn, rank_volumen, rank_valor, pct_volumen, pct_valor, n_years, n_registros]
  scalars:
    rank_volumen:    integer
    rank_valor:      integer
    n_offices:       integer
    pct_volumen:     numeric
    pct_valor:       numeric
    total_toneladas: numeric
    total_valor_mxn: numeric
# Skill determinista (sin controles aleatorios). Se comparan rank y % —
# comparar solo el rank dejaría pasar un cambio que afecte el share nacional
# sin mover la posición (p. ej. si el total nacional cambia de fuente).
comparable_value: [rank_volumen, rank_valor, pct_volumen, pct_valor]
reference: references/cabo_pulmo_national_ranking_reference.json
validation:
  params:
    office_filter: CABO SAN LUCAS
    state_filter: BAJA CALIFORNIA SUR
    year_from: 2016
    year_to: 2025
depends_on: []
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

## Data contract (minimal interface, NOT the local file)

Columns from `get_landings(group_by="office_year_fleet")`:

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `nombre_oficina` | character | — | Office name |
| `nombre_estado` | character | — | State name |
| `anio_corte` | integer | year | Year |
| `tipo_aviso` | character | — | Fleet type: `MAYORES`, `MENORES`, or `COSECHA` |
| `total_kg` | numeric | kg | Sum of landed weight (converted to `total_toneladas`, t) |
| `total_valor_mxn` | numeric | MXN (nominal) | Sum of estimated value |
| `n_records` | integer | records | Number of landing records |

Accepted aliases: `peso_desembarcado_kg` → `total_kg`, `valor_pesos_estimado` → `total_valor_mxn`.
`n_records` (name delivered by the MCP) is renamed internally to `n_registros`.

`data` covers ALL offices in the country matching `resource_group`/`species`/
`fleet_filter`/`year_from`/`year_to` — never just the focal office or state.
That is what makes the national ranking possible. `state_filter` only
identifies the focal office (step 6).

- **Aggregation unit:** office × state, summed over all years and fleets of the period.
- **Missing data:** sums use `na.rm = TRUE`; a group with `nombre_oficina` or
  `nombre_estado` = NA counts in `n_offices` with total 0.
- **Data source:** Comisión Nacional de Acuacultura y Pesca [CONAPESCA] (2026). Data
  curated by the ChatMPA team (pipeline `conapesca-database`: cleaning and species
  catalogue) from the delivery of 29 June 2026.

## Method (fixed, no degrees of freedom)

```
1. DATA ALREADY FILTERED BY MCP (resource_group/species, fleet, year)
   — the universe is ALL offices in the country, not just the focal one
   (state_filter is not sent to the tool).

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
   pct_volumen and pct_valor are rounded to 2 decimals; ranks are computed
   from the unrounded totals.

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

## Random controls
Not applicable (deterministic skill).

## Do-not rules
- Do NOT produce plots — the frontend/chatbot handles visualization.
- Do NOT identify the focal office by `nombre_oficina` alone — always use
  `nombre_oficina + nombre_estado` to avoid false matches across states.
- Do NOT mix `resource_group` and `species`.
- Do NOT send `office_filter` to the MCP query — it must stay client-side
  (used only in step 6), or the universe to rank against is lost.
- Do NOT include CPUE ranking — deferred pending pre-computation strategy.

## Validation checklist
- [ ] `sum(value$pct_volumen)` ≈ 100 (may differ slightly due to rounding).
- [ ] `rank_volumen = 1` corresponds to the office with the highest `total_toneladas`.
- [ ] Focal office present in `value` with correct scalars in `ranking`.
- [ ] `n_offices = nrow(value)`.
- [ ] Self-consistency, reference and coherence checks (validation harness, `run_checks.R`).

## Reference value and tolerance
- Reference cases: 4 (`rank_volumen`, `rank_valor`, `pct_volumen`, `pct_valor`) in
  `references/cabo_pulmo_national_ranking_reference.json`.
- Case: Cabo San Lucas landing office (BCS) against all landing offices in the
  country (156), all species and fleets, 2016–2025 (proxy for the Cabo Pulmo MPA:
  the skill resolves by landing office).
- Expected values: rank 125 (volume) and 120 (value); 0.02 % and 0.05 %, verified by
  Carolina (2026-10-01).
- Tolerance: 0 (ranks) and ±0.005 (%, the skill rounds to 2 decimals).
- Seed: not applicable.
- Status: VERIFIED.

## Success criteria
- `ranking` with 7 correct scalars for the focal office.
- `value` with all offices ranked, sorted by `rank_volumen`.

## References
- Comisión Nacional de Acuacultura y Pesca. (2026). *Avisos de arribo y de cosecha*
  [Datos sin publicar, obtenidos mediante solicitud de acceso a la información pública
  núm. 340008100012626, Plataforma Nacional de Transparencia; entregados el 29 de junio
  de 2026].
