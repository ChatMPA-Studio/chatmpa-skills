---
name: marine-prosperity-brief
domain: [conservation-policy, socioeconomics]
data-source: [MPpI]
output-type: [report]
tags: [policy-brief, prosperity-index, mppi, docx, scenarios]
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
fixed = data.replace(b'Bah\x92a', 'Bahía'.encode())     # adapt mapping per accented byte
open('data/targeted_municipalities.csv','wb').write(fixed.replace(b'\r\n', b'\n'))
```

### 2. Generate markdown briefs (R)

```bash
Rscript code/07_generate_policy_briefs.R
```

The script (see `scripts/07_generate_policy_briefs.R` for the bundled reference copy) does, per municipality:

1. **Spatial extraction** — projects the lat/lon to Mexico LCC (EPSG:6372), buffers by 30 km, intersects with `grid_sf` to get `cell_ids`.
2. **Aggregation** — `mean()` of nature/livelihood/wellbeing/balance across those cells.
3. **Limiting-axis breakdown** — counts cells by `limiting_axis` (the axis with the lowest score per cell).
4. **Category classification** — `classify_category(balance, level)`.
5. **Scenario simulation** — applies +0.15 / +0.10 / +0.05 axis perturbations, clamps to [0, 1], recomputes B, L, Pp, ranks scenarios by ΔB.
6. **Peer comparison** — joins `outputs/tables/municipal_summary.csv` and picks 3 nearest peers in (B, L) space.
7. **Markdown assembly** — fills the 11-section template (see `references/brief_structure.md`).

Output: `policy_briefs/policy_brief_<slug>.md` per municipality.

### 3. Generate the two-panel location map (Python + cartopy)

```bash
PYTHONPATH=${CHATMPA_STUDIO}/python \
  python3 policy_briefs/generate_maps.py
```

Set `CHATMPA_STUDIO` to your local checkout of the [`chatmpa-studio`](https://github.com/chatmpa-studio-lab/chatmpa-studio) repo (the `python/` subdir holds the `chatmpa` package used by these scripts).

Each map has:
- **Panel A — Regional context:** Gulf of California extent `[-118, -105, 21, 33]` by default (or custom `regional_extent` for Pacific-coast communities like Bahía de Banderas). All targeted municipalities plotted as gray dots; target shown as a coral star with white halo.
- **Panel B — Mexico minimap:** national extent `[-118, -86, 14, 33]` with a red box marking the regional extent.

When adding a new municipality, append to the `COMMUNITIES` dict:

```python
'bahia_de_kino': {
    'name': 'Bahía de Kino',
    'lon': -111.988162, 'lat': 28.84995,
    'state': 'Sonora'
},
```

For a community outside the Gulf, also set `regional_extent`:

```python
'puerto_morelos': {
    'name': 'Puerto Morelos',
    'lon': -86.875, 'lat': 20.85,
    'state': 'Quintana Roo',
    'regional_extent': [-90, -86, 18, 22],   # Caribbean extent
}
```

The map uses `cartopy.feature` Natural Earth at 10m. Brand colors come from `chatmpa.brand.COLORS` (`ocean_blue`, `light_blue`, `sand`, `coral`, `text_dark`). **Never hardcode hex.**

### 4. Build the chatMPA-branded DOCX

```bash
PYTHONPATH=${CHATMPA_STUDIO}/python \
  python3 policy_briefs/generate_docx.py
```

The DOCX builder reads each markdown brief, parses headings/lists/tables/inline bold, and produces a paginated DOCX with:

- Cover with chatMPA logo (`chatmpa.brand.LOGO_PATH`)
- Location map embedded right after the title
- Figure 1 (national prosperity 3-panel) inserted after the framework explanation
- Tables shaded with `deep_sea` headers and `light_blue` alt rows
- Page numbers in the footer
- 1-inch margins, 1.15 line spacing, Inter body + Montserrat headers (via `chatmpa.brand.FONTS`)

To add a new community:

1. Append a row to `COMMUNITY_MAP` (slug → markdown filename, map slug):
   ```python
   'bahia_de_kino': ('policy_brief_bahia_de_kino.md', 'bahia_de_kino'),
   ```
2. Append a row to `COMMUNITIES_DATA` (used by the regional consolidated report) using the metrics from the freshly generated markdown brief.

To rebuild only one DOCX without touching the consolidated report:

```python
PYTHONPATH=${CHATMPA_STUDIO}/python python3 -c "
import sys, os
sys.path.insert(0, 'policy_briefs'); os.chdir('policy_briefs')
from generate_docx import build_docx
doc = build_docx('policy_brief_<slug>.md', '<slug>', '<Community Name>')
doc.save('documents_docx/policy_brief_<slug>.docx')
"
```

### 5. Quality checks before publishing

Verify before handoff to `marine-prosperity-publish`:

- [ ] All accented characters render correctly in markdown, map, and DOCX
- [ ] The limiting axis in the brief matches the binding constraint in the data
- [ ] Scenario table shows the **Targeted** scenario as "High" efficiency when the limiting axis is below national average
- [ ] Location map shows the target as a coral star, not a gray dot
- [ ] DOCX file size is plausible (≈400–700 KB; <50 KB usually means the map didn't embed)
- [ ] Prosperity Pp value in the markdown table matches Balance × Level (round to 2 decimals)

## Quick Reference

| Step | Script | Output |
|------|--------|--------|
| 1. Prepare | manual / Numbers / Excel | `data/targeted_municipalities.csv` |
| 2. Brief markdown | `code/07_generate_policy_briefs.R` | `policy_briefs/policy_brief_<slug>.md` |
| 3. Location map | `policy_briefs/generate_maps.py` | `policy_briefs/maps/<slug>_location_map.png` |
| 4. DOCX | `policy_briefs/generate_docx.py` | `policy_briefs/documents_docx/policy_brief_<slug>.docx` |
| 5. Publish | → `marine-prosperity-publish` | NotebookLM notebook + infographic |

## Chat MPA Brand Conformance

All visual outputs from this skill MUST follow the chatMPA Studio identity:

```python
import matplotlib as mpl
from chatmpa.brand import COLORS, FONTS, LOGO_PATH, mpl_theme
mpl.rcParams.update(mpl_theme())
```

Required:
- Ocean blue for primary accents (`COLORS["ocean_blue"]`)
- Coral for the target community marker (`COLORS["coral"]`)
- Light blue for water / alternating table rows (`COLORS["light_blue"]`)
- Sand for land (`COLORS["sand"]`)
- Montserrat for display, Inter for body (`FONTS["display"]`, `FONTS["body"]`)
- `LOGO_PATH` embedded on the DOCX cover

See `BRAND_IDENTITY.md` at the chatMPA Studio repo root for the full palette.

## References

- `references/mpi_framework.md` — Full MPpI framework documentation
- `references/brief_structure.md` — 11-section brief template
- `references/scenarios.md` — Four policy-scenario specifications
- `references/targeted_municipalities_example.csv` — Example CSV input
- `scripts/07_generate_policy_briefs.R` — Reference R brief generator
- `scripts/generate_maps.py` — Reference cartopy two-panel map builder
- `scripts/generate_docx.py` — Reference DOCX builder

## Success Criteria

A successful policy brief includes:

- [ ] All three axis scores reported with national averages and status labels
- [ ] Balance, Level, Prosperity (Pp = B × L) values consistent with the brief's metric table
- [ ] Correctly-classified prosperity category
- [ ] Limiting axis identified with cell-share percentage
- [ ] Four scenarios with quantified ΔB and ΔPp
- [ ] Peer comparison (3 nearest municipalities in B × L space)
- [ ] Two-panel location map embedded in the DOCX
- [ ] Equity considerations section retained (recommend OEI follow-up)
- [ ] chatMPA Studio brand applied throughout (colors, fonts, logo)

## Handoff

When the brief is built and validated, invoke `/marine-prosperity-publish` with the slug to upload to NotebookLM and generate the infographic.
