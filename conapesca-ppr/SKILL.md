---
name: conapesca-ppr
version: 0.1.0
tier: 1
description: >
  Estimate the ecological footprint of a fishery by calculating the Primary
  Production Required (PPR) to sustain observed catches at a marine protected
  area or state. Fires on questions about how much primary production or
  phytoplankton the fishery consumes, what the trophic footprint of a species
  or fleet is, or whether fishing pressure is ecologically costly relative to
  the trophic level of the target species.
inputs:
  species:
    type: array
    required: true
    description: >
      One or more canonical scientific names (`nombre_cientifico_canonico`).
      Must match the database exactly.
  state_filter:
    type: string
    required: true
    description: >
      Estado de la oficina de desembarque (`nombre_estado`). Defines regional
      scope and disambiguates office names across states.
  office_filter:
    type: string
    required: false
    description: >
      Landing office (`nombre_oficina`) within `state_filter`. If provided,
      adds local-scale series. Never use without `state_filter`.
  ww_to_carbon:
    type: number
    required: false
    default: 9
    description: >
      Wet-weight-to-carbon conversion ratio (kg wet wt per kg C). Default 9
      per Pauly & Christensen (1995).
  te:
    type: number
    required: false
    default: 0.1
    description: >
      Trophic transfer efficiency. Must be in (0, 1). Default 0.1.
  tl_override:
    type: named_numeric
    required: false
    description: >
      User-supplied trophic level per species, e.g. {"Lutjanus peru": 3.2}.
      Takes precedence over catalog values. Required when any species has
      NA trophic_level in the catalog.
acquire:
  - source: payload
    as: data
    provider:
      server: conapesca
      tool: get_landings
      args:
        group_by: folio
      params:
        especie: nombre_cientifico_canonico
        estado: nombre_estado
        oficina: nombre_oficina
    columns:
      - anio_corte
      - tipo_aviso
      - nombre_estado
      - nombre_oficina
      - nombre_cientifico_canonico
      - trophic_level
      - peso_desembarcado_kg
# Sin `output.table`: run_skill() devuelve un solo data.frame.
# Skill determinista — fórmula cerrada, sin resampling.
comparable_value: [ppr_kg_c, trophic_level_used]
reference: references/cabo_pulmo_ppr_reference.json
validation:
  params:
    species: [Lutjanus argentiventris]
    state_filter: BAJA CALIFORNIA SUR
    office_filter: CABO SAN LUCAS
depends_on: []
---

# CONAPESCA — Primary Production Required (PPR)

## Purpose

Quantifies how much primary production (in carbon units) is required to
sustain the observed landings of one or more species at regional (state) and
local (office) scales, for MAYORES and MENORES fleets separately. Uses the
Pauly & Christensen (1995) formulation with a fixed wet-weight-to-carbon
conversion and trophic transfer efficiency, both user-overridable.

**Reference:** Pauly D. & Christensen V. (1995). Primary production required
to sustain global fisheries. *Nature*, 374, 255–257.

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `species` | chr vector | required | One or more `nombre_cientifico_canonico` |
| `state_filter` | chr | required | `nombre_estado` — defines regional scope and disambiguates office names |
| `office_filter` | chr / NULL | NULL | `nombre_oficina` — if provided, adds local-scale series |
| `ww_to_carbon` | num | 9 | Wet-weight-to-carbon conversion ratio (kg wet wt per kg C) |
| `te` | num | 0.1 | Trophic transfer efficiency (0 < te < 1) |
| `tl_override` | named num / NULL | NULL | User-supplied TL per species, e.g. `c("Lutjanus peru" = 3.2)`. Used only when `trophic_level` is NA in the catalog. |

## Data contract (minimal interface, NOT the local file)

Individual landing records from the CONAPESCA MCP (no folio-level grouping
required — `peso_desembarcado_kg` is additive across records).

**Required columns:**

| Column | Type | Notes |
|--------|------|-------|
| `anio_corte` | int | Reference year |
| `tipo_aviso` | chr | "MAYORES" or "MENORES" (COSECHA excluded) |
| `nombre_estado` | chr | State name |
| `nombre_oficina` | chr | Landing office name |
| `nombre_cientifico_canonico` | chr | Canonical scientific name |
| `trophic_level` | num | From FishBase via species catalog; may be NA |
| `peso_desembarcado_kg` | num | Wet weight landings |

**Missing-data rule:**
- Exclude records where `peso_desembarcado_kg <= 0` or `is.na(peso_desembarcado_kg)`.
- No other quality filters applied — PPR does not use effort or date-derived
  fields, so `flag_fecha_generica` and `flag_dias_efectivos_sospechoso` are
  irrelevant here.

**Aggregation unit:** AMP-year (one PPR value per
`anio_corte × tipo_aviso × escala × nombre_cientifico_canonico`).

## Method (fixed, no degrees of freedom)

**Formula (Pauly & Christensen 1995):**

```
PPR_kg_C = (peso_total_kg / ww_to_carbon) × (1 / te)^(TL − 1)
```

With defaults `ww_to_carbon = 9` and `te = 0.1`, this reduces to:

```
PPR_kg_C = (peso_total_kg / 9) × 10^(TL − 1)
```

**Steps:**

1. Filter records: `tipo_aviso %in% c("MAYORES", "MENORES")`,
   `peso_desembarcado_kg > 0`, `nombre_estado == state_filter`,
   `nombre_cientifico_canonico %in% species`.

2. **Resolve trophic level per species:**
   - Use `trophic_level` from catalog (mean value from FishBase).
   - If `trophic_level` is NA for any requested species AND no `tl_override`
     is provided for that species: **stop with an error** listing which species
     are missing TL, and ask the user to supply values via `tl_override`.
   - If `tl_override` is provided for a species: use it regardless of whether
     catalog value exists (override takes precedence). Record `tl_source =
     "override"`.
   - Otherwise: `tl_source = "catalog"`.

3. **Aggregate catch** by `anio_corte × tipo_aviso × nombre_cientifico_canonico`
   at regional scale (full state) and, if `office_filter` is provided, at local
   scale (filtered to `nombre_oficina == office_filter`):
   ```
   peso_total_kg = sum(peso_desembarcado_kg)
   n_registros   = n()
   ```

4. **Apply PPR formula** to each row:
   ```
   PPR_kg_C = (peso_total_kg / ww_to_carbon) × (1 / te)^(TL − 1)
   ```

5. Return combined regional + local results (if applicable).

## Random controls

Not applicable — deterministic skill (closed-form formula, no resampling).

## Reference value and tolerance

- Reference case: PENDING — PPR for Cabo Pulmo (state: BAJA CALIFORNIA SUR,
  office: CABO SAN LUCAS) for *Lutjanus argentiventris*, full available series,
  to be verified by Edu/Fabio against a direct calculation in R.
- Tolerance: ± 0.01 kg C (rounding only — formula is deterministic).
- Status: PENDING. Stored in `references/cabo_pulmo_ppr_reference.json`.
  Do NOT fill expected values until human-verified.

## Do-not rules

- Do NOT proceed if any requested species has `trophic_level = NA` and no
  `tl_override` — stop and list missing species for the user.
- Do NOT accept `te <= 0` or `te >= 1` — nonsensical transfer efficiency.
- Do NOT accept `ww_to_carbon <= 0`.
- Do NOT warn or error on `trophic_level` outside [1, 5] — unusual but valid
  for some invertebrates or apex predators; report the value and let the user
  judge.
- Do NOT apply `flag_fecha_generica` or `flag_dias_efectivos_sospechoso`
  filters — PPR uses only catch weight, not effort or date-derived fields.
- Do NOT aggregate PPR across species — return one row per species. Summation
  across species is the caller's responsibility.
- Do NOT mix MAYORES and MENORES — always separate.
- Do NOT use `tl_override` silently — always report `tl_source` in the output
  so the user knows which TL values entered the formula.

## Validation checklist

- [ ] self-consistency: run N times on fixed data, outputs match exactly
      (deterministic — tolerance = 0).
- [ ] reference: output matches `references/cabo_pulmo_ppr_reference.json`
      within tolerance. PENDING → SKIP with disclosure until verified.
- [ ] coherence: output declares `formula_used`, `ww_to_carbon`, `te`, and
      `tl_source` per species, matching this contract.

## Success criteria

A complete PPR analysis includes:

- PPR reported per `anio_corte × tipo_aviso × escala ×
  nombre_cientifico_canonico` in kg C.
- `trophic_level_used` and `tl_source` ("catalog" or "override") reported for
  every species — never implicit.
- `peso_desembarcado_kg_total` reported alongside PPR (allows reader to
  back-calculate and verify).
- `formula_used`, `ww_to_carbon`, and `te` declared in output metadata.
- `n_registros` reported per row (number of landing records aggregated).
- If any `tl_override` was used: explicit disclosure in the output narrative.
- If `ww_to_carbon` or `te` differ from defaults: explicit disclosure.

---

## Planned scale architecture — PENDING: gradilla costera + base limpia

> Este bloque documenta la arquitectura objetivo del MVP. No modifica el
> contrato actual. Implementar cuando la gradilla y los puertos de desembarque
> georreferenciados estén disponibles.

### Cambio de escala local
- **Actual**: `office_filter` (nombre_oficina) como proxy del AMP
- **Planeado**: sitios de desembarque georreferenciados asociados a celdas de
  la gradilla donde `nombre_amp == <amp_name>`
- Misma lógica que `conapesca-cpue` — cambio paralelo

### Cambio de escala regional
- **Actual**: `state_filter` (nombre_estado)
- **Planeado**: `region_id` de `conapesca-lfo-regions`
- PPR regional = suma de capturas de todos los folios de la región / PPR agregado
- Supuesto: no traslape de localidades entre oficinas dentro de la región

### Lo que NO cambia
- Fórmula PPR: Pauly & Christensen (1995) — idéntica
- Niveles tróficos y parámetros `ww_to_carbon`, `te`
- Separación MAYORES/MENORES

### Dependencias para implementar
- [ ] Gradilla costera disponible (sf con `nombre_amp`, `region_id`, `nombre_oficina`)
- [ ] Puertos de desembarque georreferenciados en la base CONAPESCA
- [ ] `conapesca-lfo-regions` ejecutado
- [ ] Parámetro `region_filter` agregado como alternativa a `state_filter`
