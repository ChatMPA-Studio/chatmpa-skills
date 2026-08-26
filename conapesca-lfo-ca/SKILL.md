---
name: conapesca-lfo-ca
version: 0.1.0
tier: 2
description: >
  Assess whether commercial fisheries offices in Mexico show distinct spatial
  structure based on the composition and volume of their landings. Fires when
  the user asks whether landing offices can be grouped into fishing regions,
  whether there is a spatial gradient in catch composition across offices, or
  as a prerequisite to regionalizing fishing pressure for downstream analyses.
  Must be run before conapesca-lfo-regions.
inputs:
  tax_resolution:
    type: string
    required: false
    enum: [nombre_especie, genus, family, nombre_cientifico]
    default: nombre_especie
    description: >
      Taxonomic grouping column for the landing matrix. "nombre_especie"
      (CONAPESCA resource group) is closest to Erisman et al. (2011) species groups.
  year_min:
    type: integer
    required: false
    default: 2001
    description: >
      First year of the analysis period. PENDING — verify with Edu/Fabio that
      data coverage is adequate from this year across all LFOs.
  year_max:
    type: integer
    required: false
    default: 2010
    description: >
      Last year of the analysis period. PENDING — verify with Edu/Fabio whether
      2010 is conservative enough to avoid depletion or climate-shift effects.
  lfo_coords:
    type: dataframe
    required: false
    description: >
      Optional. Columns: nombre_oficina_canonico (chr), lat (num), lon (num).
      If provided, enables spatial correlation of CA axis 2 with lat/lon.
  k_range:
    type: integer_vector
    required: false
    default: "3:12"
    description: >
      Range of k values for WK and KL index computation. At least 2 values required.
acquire:
  # El orquestador hace múltiples calls al MCP CONAPESCA (uno por año o estado)
  # porque get_landings topa en 2000 filas con group_by=NULL, los concatena,
  # y manda la tabla en el body.
  - source: payload
    as: data
    provider:
      server: conapesca
      tool: get_landings
      args:
        group_by: folio
      params:
        estado: nombre_estado
    columns:
      - anio_corte
      - tipo_aviso
      - nombre_oficina_canonico
      - nombre_especie
      - peso_desembarcado_kg
output:
  table: kl_table
# CA es determinista; k-means con seed=42. Se compara el k óptimo (KL) y el
# MLG (gradiente máximo, determina si CA es el método correcto).
comparable_value: [k_optimal_kl, mlg]
reference: references/nwmexico_ca_reference.json
validation:
  params:
    tax_resolution: nombre_especie
    year_min: 2001
    year_max: 2010
depends_on: []
---

# CONAPESCA LFO — Correspondence Analysis

## Purpose

Determines whether spatial structure exists in the commercial landings of
CONAPESCA offices by building a landing-office × resource-group matrix and
running DCA + CA following Erisman et al. (2011). Produces CA ordination
scores, variance explained, and quality indices (WK, KL) for a range of k
values to inform the user's choice of number of fishing regions in the
downstream skill `conapesca-lfo-regions`.

**Reference:** Erisman B.E. et al. (2011). Spatial structure of commercial
marine fisheries in Northwest Mexico. *ICES Journal of Marine Science*, 68(3),
564–571. doi:10.1093/icesjms/fsq179

## Data contract (minimal interface, NOT the local file)

### Required: `data`
Data frame of individual or folio-level landing records from the CONAPESCA MCP
(`get_landings()` with no group_by, or group_by = "folio"). Required columns:

| Column | Type | Description |
|--------|------|-------------|
| `anio_corte` | integer | Landing year |
| `tipo_aviso` | character | Fleet type: `MAYORES` or `MENORES` |
| `litoral` | character | Coast: `PACIFICO` or `GOLFO` |
| `nombre_oficina` | character | Landing office name |
| `nombre_especie` | character | CONAPESCA resource group name (always required) |
| `genus` | character | Genus (required only if `tax_resolution = "genus"`) |
| `family` | character | Family (required only if `tax_resolution = "family"`) |
| `nombre_cientifico` | character | Scientific name (required only if `tax_resolution = "nombre_cientifico"`) |
| `peso_desembarcado_kg` | numeric | Landed weight in kg |

Records with `NA` or empty resource-group values are excluded silently.
`COSECHA` records are excluded. No other quality filters are applied here —
the matrix represents total landings volume, not CPUE.

**Note on MCP data pull:** the current `conapesca-db-mcp` `get_landings` tool
caps at 2000 rows per call when `group_by = NULL`. For a full multi-year,
multi-office pull the orchestrator must make multiple calls (e.g. one per year
or one per state) and concatenate results before passing to this skill.

### Optional: `lfo_coords`
Data frame with columns `nombre_oficina` (chr), `latitud_oficina` (num),
`longitud_oficina` (num). If provided, enables the spatial correlation step
(CA axis 2 scores vs. latitude and longitude). If `NULL`, that step is
skipped and reported as PENDING.

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `litoral` | character | — **required** | Coast to analyze: `"PACIFICO"` or `"GOLFO"`. No default — must be specified explicitly. Pacific and Gulf offices must never be mixed in the same CA: their catch compositions are ecologically incomparable and would produce a spurious first axis driven by coast, not fishery structure. Run the skill separately for each litoral. |
| `tax_resolution` | character | `"nombre_especie"` | Taxonomic grouping column. Options: `"nombre_especie"` (CONAPESCA resource group — closest to Erisman's species groups), `"genus"`, `"family"`, `"nombre_cientifico"` (species-level binomial). |
| `year_min` | integer | `2001` | First year of the analysis period. **PENDING** — verify with Edu/Fabio. |
| `year_max` | integer | `2010` | Last year of the analysis period. **PENDING** — verify with Edu/Fabio whether 2010 is sufficiently conservative to avoid strong depletion or climate-shift effects. |
| `k_range` | integer vector | `3:12` | Range of k values for WK and KL index computation. |

**PENDING design decisions (verify with Edu/Fabio before production use):**
- `year_min` / `year_max`: 2001–2010 chosen to balance representativeness
  and avoidance of documented stock collapses and climate shifts in the Gulf.
- `temporal_resolution`: mean annual kg used (each year weighted equally).
  Alternative is period totals. Mean annual is preferred because it prevents
  exceptional years (El Niño, stock pulses) from dominating the matrix.

## Method (fixed, no degrees of freedom)

### Step 1 — Filter and aggregate
- Keep records where `litoral == litoral` parameter, `anio_corte` ∈
  [`year_min`, `year_max`], and `tipo_aviso` ∈ {`MAYORES`, `MENORES`}.
- Sum `peso_desembarcado_kg` by (`nombre_oficina`, `tax_group`,
  `anio_corte`) → annual totals per LFO × resource group.
- Take `mean()` across years → **mean annual kg** per LFO × resource group.
- Pivot wide: rows = LFOs, columns = resource groups, values = mean annual kg.
  Absent combinations are filled with 0.

### Step 2 — DCA to select ordination method
`vegan::decorana(matrix_lfo)` on raw (untransformed) data.
Maximum gradient length (MLG) = max − min of axis 1 site scores.
- MLG > 3 SD → CA preferred (unimodal response) → proceed with CA.
- MLG ≤ 3 SD → RDA preferred (linear response) → noted in output; CA still
  run for comparability with Erisman, but flagged.

### Step 3 — Correspondence Analysis
`vegan::cca(vegan::downweight(matrix_lfo))`.
Rare resource groups downweighted (`vegan::downweight`) to improve ordination
as in Erisman et al. (2011).
Extracts: site scores (LFOs), species scores (resource groups), eigenvalues,
percent variance explained per axis.

### Step 4 — Spatial correlation (if `lfo_coords` provided)
Pearson rank correlation of CA axis 2 scores with `latitud_oficina` and
`longitud_oficina` of each LFO, following Erisman et al. (2011).
Reports: r, p-value, 95% CI for each correlation.

### Step 5 — WK and KL indices
For each k ∈ (`min(k_range)` − 1) : (`max(k_range)` + 1):
- `set.seed(42)`, `kmeans(ca_scores[, 1:2], centers = k, nstart = 25,
  iter.max = 100)`.
- WK(k) = `km$tot.withinss` (pooled within-cluster sum of squares).

KL index (Krzanowski & Lai, 1988) for k ∈ `k_range`:
```
DIFF(k)   = (k-1)^(2/p) × WK(k-1) - k^(2/p) × WK(k)
DIFF(k+1) = k^(2/p) × WK(k) - (k+1)^(2/p) × WK(k+1)
KL(k)     = |DIFF(k)| / |DIFF(k+1)|
```
where p = number of CA axes used (2).
Optimal k = argmax KL(k). Reported alongside WK for the user to decide.

**Reference:** Krzanowski W.J. & Lai Y.T. (1988). A criterion for determining
the number of groups in a data set using sum-of-squares clustering.
*Biometrics*, 44, 23–34.

## Random controls

Seed `42` is used inside the WK/KL computation loop (k-means for index
estimation only). The CA itself is deterministic.

## Reference value and tolerance

- Reference case: PENDING — WK and KL table for NW Mexico (all LFOs,
  2001–2010, `tax_resolution = "nombre_especie"`) to be verified against
  Erisman et al. (2011) results where comparable. Expected: MLG > 3 SD,
  k_optimal_kl near 8.
- Tolerance: PENDING.
- Status: PENDING. Stored in `references/nwmexico_ca_reference.json`.
  Do NOT invent reference values.

## Do-not rules

- Do NOT mix offices from different litorales (PACIFICO + GOLFO) in the same
  CA run — their catch compositions are ecologically incomparable and the
  inter-coast contrast would dominate axis 1, masking real fishery structure.
  Run the skill separately for each litoral.
- Do NOT transform the matrix before CA (use raw kg as Erisman did — DCA
  confirmed this is appropriate when MLG > 3).
- Do NOT sum `dias_efectivos` or compute CPUE — this skill uses landed weight
  only, not effort-normalized catch.
- Do NOT include `COSECHA` records — aquaculture, not fishing pressure.
- Do NOT run k-means inside this skill to produce final clusters — only for
  index computation. Final clustering is `conapesca-lfo-regions`.
- Do NOT proceed with CA if fewer than 5 LFOs have data — results would be
  meaningless.
- Do NOT interpret CA axis 1 and axis 2 directions without checking the
  spatial correlation output — axis orientation depends on the data.

## Validation checklist

- [ ] self-consistency: run twice on fixed data, CA scores and WK/KL table
      match exactly (CA is deterministic; k-means uses fixed seed).
- [ ] reference: output matches `references/nwmexico_ca_reference.json`.
      PENDING → SKIP with disclosure.
- [ ] coherence: MLG reported; method_chosen matches MLG threshold;
      WK and KL computed for full k_range.

## Success criteria

A complete CA run includes:
- `matrix_lfo`: wide data.frame (LFOs × resource groups, mean annual kg).
- `ca_scores_lfo`: data.frame with CA1, CA2 per LFO.
- `eigenvalues`: table with axis, eigenvalue, pct_variance for all axes.
- `mlg`: DCA maximum gradient length; `method_chosen` = "CA" or "RDA".
- `kl_table`: data.frame with k, WK, KL for all k in k_range;
  `k_optimal_kl` = argmax KL.
- `spatial_correlation`: list with r, p-value for CA2 vs `latitud_oficina`
  and `longitud_oficina`, or `NULL` if `lfo_coords` not provided (disclosed in output).
- `pending_params` declared in `params`.
