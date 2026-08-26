---
name: conapesca-lfo-regions
version: 0.1.0
tier: 2
description: >
  Cluster CONAPESCA fishing offices into discrete fishing regions based on
  the similarity of their catch composition, and produce a lookup table
  assigning each office to a region. Fires after the user has reviewed the
  CA ordination and quality indices from conapesca-lfo-ca and has decided
  on the number of regions. The output lookup is consumed by downstream
  skills that require regional fishing pressure (e.g. conapesca-cpue at
  regional scale). Must be preceded by conapesca-lfo-ca.
inputs:
  k:
    type: integer
    required: true
    description: >
      Number of fishing regions (clusters). Must satisfy 2 ≤ k ≤ n_lfo − 1.
      Chosen by the user after reviewing the WK/KL table from conapesca-lfo-ca.
      The k_optimal_kl from that skill is a suggestion, not a mandate.
acquire:
  - source: skill_output
    skill: conapesca-lfo-ca
    as: ca_output
    fields: [ca_scores_lfo, kl_table, k_optimal_kl]
output:
  table: lookup
# k-means con seed=42 — determinista. Se compara el WK final (within-cluster SS)
# para detectar si el clustering corrió con la misma semilla.
comparable_value: [wk_final]
reference: references/nwmexico_regions_reference.json
validation:
  params:
    k: 7
depends_on: [conapesca-lfo-ca]
---

# CONAPESCA LFO Regions — k-means clustering and region lookup

## Purpose

Partitions CONAPESCA landing offices into k discrete fishing management regions using
k-means clustering on CA ordination scores produced by `conapesca-lfo-ca`.
Regions are renumbered geographically (north to south) for consistency across
runs. Produces a canonical lookup table (`nombre_oficina` → `region_id`)
for use by all downstream skills that consume regional fishing pressure data.

**Reference:** Erisman B.E. et al. (2011). Spatial structure of commercial
marine fisheries in Northwest Mexico. *ICES Journal of Marine Science*, 68(3),
564–571. doi:10.1093/icesjms/fsq179

## Data contract (minimal interface, NOT the local file)

### Required: `ca_output`
The complete list returned by `conapesca-lfo-ca$run_skill()`. Must contain:
- `ca_output$value$ca_scores_lfo` — data.frame with CA1, CA2 per LFO
  (row names = `nombre_oficina`).
- `ca_output$value$kl_table` — data.frame with k, WK, KL (for reference
  in the output; not recomputed here).
- `ca_output$value$k_optimal_kl` — integer suggested by KL index.

### Required: `k`
Integer. Number of clusters chosen by the user after reviewing the WK and
KL table from `conapesca-lfo-ca`. Must satisfy 2 ≤ k ≤ n_lfo − 1.

## Method (fixed, no degrees of freedom)

### Step 1 — k-means clustering
`set.seed(42)`, then:
```r
kmeans(ca_scores_lfo[, c("CA1", "CA2")],
       centers  = k,
       nstart   = 25,
       iter.max = 100)
```
Euclidean distances in CA score space. Raw cluster labels are arbitrary
(depend on centroid initialization) and are not used as final identifiers.

### Step 2 — Geographic renumbering (north to south)
To ensure `region_1` always refers to the northernmost cluster regardless
of k-means initialization:
1. Compute the mean CA axis 2 score for each raw cluster.
   (CA axis 2 correlates positively with latitude — verified in
   `conapesca-lfo-ca` spatial correlation step; used as lat proxy here
   because explicit lat/lon may not always be available.)
2. Rank clusters by descending mean CA2 score:
   rank 1 = highest mean CA2 = most temperate = northernmost.
3. Assign `region_id = paste0("region_", rank)` and `region_num = rank`.

This renumbering is deterministic given the k-means result and CA scores.

### Step 3 — MDS verification
`stats::cmdscale(dist(ca_scores_lfo[, c("CA1", "CA2")]), k = 2)`.
Returns 2D MDS coordinates per LFO with their assigned region — intended
for visual verification that regions do not overlap in ordination space,
following Erisman et al. (2011). No statistical test is applied.

### Step 4 — Cluster summary
Per region: number of LFOs, list of office names, mean CA1 and CA2 scores,
total and mean annual landings (if available from `ca_output$value$matrix_lfo`).
A `region_label_suggested` field is left as `NA` in the skill output — the
orchestrator (LLM) should fill this with a descriptive geographic name based
on the office names and their known locations, for communication purposes only.
The canonical identifier is always `region_id` (e.g. `"region_1"`).

## Random controls

Seed: **42**. Applied immediately before `kmeans()`. Fixed — do not change
without updating SKILL.md and incrementing skill_version.
`nstart = 25` and `iter.max = 100` are also fixed.

## Reference value and tolerance

- Reference case: PENDING — cluster assignments for NW Mexico (k chosen by
  user after reviewing KL table) to be verified by Edu/Fabio against an
  independent k-means run in R on the same CA scores.
- Tolerance: exact match expected (deterministic given seed and k).
- Status: PENDING. Stored in `references/nwmexico_regions_reference.json`.

## Do-not rules

- Do NOT run this skill without a `ca_output` from `conapesca-lfo-ca` — the
  CA scores are the only valid input for clustering.
- Do NOT mix `ca_output` objects from different litorales — each regionalization
  must correspond to a single litoral (PACIFICO or GOLFO). The `litoral` is
  set at the `conapesca-lfo-ca` step and inherited here via `ca_output`.
- Do NOT use raw landings or geographic distance as clustering inputs —
  composition similarity in CA space is the basis, as in Erisman et al.
- Do NOT auto-select k — the user must choose it after reviewing WK/KL.
  The `k_optimal_kl` from `conapesca-lfo-ca` is a suggestion, not a mandate.
- Do NOT use `region_label_suggested` as a canonical identifier in downstream
  skills — only `region_id` and `region_num` are reproducible.
- Do NOT renumber regions by geographic coordinates (lat/lon) if explicit
  coordinates are available — always use CA2 score as the ordering basis so
  the method is consistent regardless of whether lfo_coords were provided
  to the upstream skill.
- Do NOT interpret the MDS plot as a separate ordination — it is a
  verification tool derived from the same CA scores, not an independent
  analysis.

## Validation checklist

- [ ] self-consistency: run twice with same `ca_output` and `k`,
      `region_id` assignments match exactly (deterministic with seed 42).
- [ ] reference: output matches `references/nwmexico_regions_reference.json`.
      PENDING → SKIP with disclosure.
- [ ] coherence: `region_num` runs 1 to k; northernmost cluster = region_1;
      all LFOs in `ca_output$value$ca_scores_lfo` appear in lookup.

## Success criteria

A complete regionalization includes:
- `lookup`: data.frame with one row per LFO —
  `nombre_oficina`, `region_id`, `region_num`.
- `cluster_summary`: one row per region — `region_id`, `region_num`,
  `n_lfo`, `lfo_names`, `mean_ca1`, `mean_ca2`,
  `region_label_suggested` (NA — to be filled by orchestrator).
- `mds_coords`: data.frame with `nombre_oficina`, `MDS1`, `MDS2`,
  `region_id` — for verification plot.
- `k_used` and `wk_final` reported.
- `k_optimal_kl` from upstream skill disclosed in params.
