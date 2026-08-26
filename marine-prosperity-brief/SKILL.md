---
name: marine-prosperity-brief
domain: [conservation-policy, socioeconomics]
data-source: [MPpI]
output-type: [report]
tags: [policy-brief, prosperity-index, mppi, docx, scenarios]
peer_reviewed: true
status: stable
version: 0.2.0
description: This skill generates Marine Prosperity Index (MPpI) policy briefs for coastal municipalities. It runs the analytical pipeline (axis normalization → 30 km buffer extraction → metric aggregation → policy-scenario simulation), assembles a structured markdown brief, produces a two-panel location map with cartopy, and converts everything into a chatMPA-branded DOCX. Use this skill when the user asks to "create a policy brief", "generate an MPI brief", "build a marine prosperity report", "add a municipality to the briefs", or mentions targeted_municipalities.csv. TRIGGER on phrases like "policy brief for <place>", "MPpI brief", "marine prosperity report", "Pp for <community>", "Balance × Level brief", or any request that combines a coastal municipality name with a request to produce a report or assessment.
---

# Marine Prosperity Index — Policy Brief Builder

## Purpose

This skill produces a complete Marine Prosperity Index (MPpI) policy brief for any coastal municipality in Mexico (or any region where a comparable axis-score grid exists). It guides the researcher through:

- Extracting MPpI scores from a coastal grid within a buffer of a target point
- Computing the three axes (Nature, Livelihood, Well-being), Balance, Level, and the composite Prosperity (Pp = B × L)
- Classifying the region into one of four prosperity categories
- Simulating four policy scenarios (Targeted, Sustainable, Conservation, Integrated)
- Writing a structured markdown brief
- Generating a two-panel cartopy location map (regional context + Mexico minimap)
- Building a chatMPA-branded DOCX with embedded map and Figure 1

## When to Use This Skill

Use this skill when:
- The user names a coastal community and asks for a policy brief, MPpI assessment, or "Pp report"
- The user has edited `targeted_municipalities.csv` and asks to "rerun the pipeline"
- The user wants to add a new municipality to the regional brief collection
- The user mentions Balance, Level, or Prosperity scores for a specific place
- The user references the four policy scenarios

Do NOT use this skill for:
- National-scale MPpI mapping (use the manuscript's scripts 03/06 directly)
- LTEM fish-community questions (use `ltem-fish-community`)
- Reef coverage analysis (use `reef-ecology-report`)
- Publishing briefs to NotebookLM / generating infographics (use `marine-prosperity-publish`)

## Conceptual Framework

The MPpI evaluates coastal grid cells (≈5 km, 0.05°) across three axes:

| Axis | Indicators | Examples |
|------|-----------|----------|
| **Nature** | 13 | Biodiversity, mangrove extent, MPA coverage, water quality, carbon storage |
| **Livelihood** | 12 | GDP, fisheries production, employment, investment, tourism |
| **Well-being** | 23 | Education, health coverage, household services, poverty (CONEVAL), governance |

All indicators are min-max normalized to [0, 1] with 1% / 99% winsorization. Negatively-signed indicators (e.g. poverty rate) are direction-reversed before aggregation.

### Key metrics

```
Balance (B) = (E − 1/3) / (2/3),  where E = (Σxᵢ)² / (n · Σxᵢ²)        # evenness, B ∈ [0, 1]
Level   (L) = (Nature + Livelihood + Well-being) / 3
Prosperity (Pp) = Balance × Level
```

- High balance (B ≥ 0.75) → no axis lagging severely
- High level (L ≥ 0.40) → strong overall performance
- Viability threshold: any axis < 0.20 demands priority rescue regardless of B

### Four prosperity categories

| Category | Balance | Level | Strategy |
|----------|---------|-------|----------|
| Balanced Prosperity | ≥ 0.75 | ≥ 0.40 | Maintain trajectory; strengthen limiting axis |
| Balanced but Developing | ≥ 0.75 | < 0.40 | Broad uplift across all axes |
| Imbalanced Growth | < 0.75 | ≥ 0.40 | Target the binding constraint |
| Lagging | < 0.75 | < 0.40 | Urgent priority on weakest axis |

Nationally, **Livelihood is the binding constraint in 88% of coastal cells**, Nature in 9%, Well-being in 3% — make sure recommendations match the *local* limiting axis, not the national pattern.

See `references/mpi_framework.md` for the full conceptual reference.

## Data Inputs

The skill assumes a Marine Prosperity Index project laid out like the canonical manuscript repo:

```
<project>/
├── data/
│   ├── targeted_municipalities.csv             # municipality, lon, lat  (UTF-8!)
│   ├── prosperity_variables_classification.xlsx
│   ├── cost_template.csv                       # reference unit costs per axis
│   └── feedback_parameters.csv
└── outputs/
    ├── grid_sf_clean.rds                       # sf grid (3236 cells in MX example)
    ├── normalized_scores.rds                   # nature, livelihood, wellbeing, balance, limiting_axis
    └── tables/municipal_summary.csv            # optional, enables peer comparison
```

**Encoding warning:** `targeted_municipalities.csv` must be UTF-8. Names with accents written from macOS Numbers often save as MacRoman (`í` becomes `0x92`). Verify with `file data/targeted_municipalities.csv` and rewrite as UTF-8 before running the R pipeline, otherwise the slug helper and map labels will be corrupted (`Bah?a de Kino` → `bah_a_de_kino`).

If `outputs/normalized_scores.rds` does not exist, run `code/01_load_and_prepare_data.R` then `code/02_normalize_and_aggregate.R` first. The brief generator depends on those outputs and on `outputs/grid_sf_clean.rds`.

## Core Workflow

### 1. Validate inputs

```bash
# Check encoding
file data/targeted_municipalities.csv          # → should be: CSV text, UTF-8 (or ASCII)

# Check upstream RDS exists
Rscript -e 'stopifnot(file.exists("outputs/normalized_scores.rds"),
                      file.exists("outputs/grid_sf_clean.rds"))'
```

If encoding is wrong:
```python
data = open('data/targeted_municipalities.csv','rb').read()
