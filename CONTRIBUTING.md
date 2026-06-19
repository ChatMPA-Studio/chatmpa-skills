# Contributing a chatMPA Studio skill

This repository is a curated library of [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills) for marine science. Every skill follows one **canonical format** so the library stays consistent, discoverable, and machine-indexable. This document is the authoritative spec; `tools/build_index.py` validates each skill against it on every push.

When you add or change a skill, the catalog (`INDEX.md`, `catalog.json`, and the README skills table) is **regenerated automatically** by a GitHub Action — you never edit those by hand.

------------------------------------------------------------------------

## 1. Folder layout

Each skill lives in its own top-level directory whose name **must equal** the skill's `name` frontmatter field (kebab-case):

```         
<skill-name>/
├── SKILL.md          # REQUIRED — definition, triggers, taxonomy, workflow
├── references/       # OPTIONAL — domain reference docs (methodology, guides, vocab)
├── scripts/          # OPTIONAL — helper scripts invoked by the skill
└── assets/           # OPTIONAL — templates, logos, fixtures
```

Only `SKILL.md` is required. Use `references/` for prose the model reads on demand, `scripts/` for code it runs, and `assets/` for binary or template files.

**Naming rules:** - `<skill-name>` is kebab-case (`lowercase-with-hyphens`), English, descriptive. - Folder name **==** the `name` frontmatter field. The indexer fails the build if they differ. - Reference and script filenames are English and kebab- or snake-case.

------------------------------------------------------------------------

## 2. Required frontmatter

`SKILL.md` begins with a YAML frontmatter block. These fields are **required** and validated:

``` yaml
---
name: skill-name-in-kebab-case
description: >-
  One to three sentences. State what the skill does (active verbs), who uses it,
  and the trigger phrases that should invoke it. Include a "Do NOT use for…"
  cross-reference to related skills where relevant.
domain: [conservation-policy, fisheries-ecology]
data-source: [LTEM]
output-type: [analysis, report]
tags: [diversity, trophic, size-structure]
status: experimental
version: 0.1.0
# optional provenance (recommended):
author: jane-doe
---
```

| Field | Type | Rule |
|------------------------|------------------------|------------------------|
| `name` | string | kebab-case; must equal the folder name |
| `description` | string | 1–3 sentences; what / who / trigger phrases; the Claude Code loader uses this to decide invocation |
| `domain` | list | one or more values from the **domain** vocabulary (§4) |
| `data-source` | list | one or more values from the **data-source** vocabulary (§4) |
| `output-type` | list | one or more values from the **output-type** vocabulary (§4) |
| `tags` | list | free-form lowercase keywords for retrieval (no controlled list) |
| `status` | string | lifecycle stage: `experimental` (default for new skills), `stable`, or `deprecated` (see [`QUALITY.md`](./QUALITY.md)) |
| `version` | string | semver `MAJOR.MINOR.PATCH`; new skills start at `0.1.0`. Bump on change (see [`QUALITY.md`](./QUALITY.md) → Versioning) |

**Optional provenance field** (recommended, not required): `author` (submitter handle). Surfaced in the catalog when present.

`name` and `description` are consumed by Claude Code itself. The remaining fields are used by the indexer and quality gates — the Claude Code loader ignores unknown frontmatter keys, so they are safe to add.

New skills land as `status: experimental`. Promotion to `stable` happens through review against the quality bar in [`QUALITY.md`](./QUALITY.md). The full set of automated checks (errors that block, warnings that advise) is documented there.

------------------------------------------------------------------------

## 3. Required body sections

Write the body in **English**. (A skill may *produce* output in another language — see §6 — but its instructions are always English.) Use this canonical section order; omit a section only when it genuinely does not apply:

``` markdown
# Title

## Purpose
Who uses this, what it does, what outcomes it produces.

## When to Use This Skill
**Use when:** …
**Do NOT use for:** … (→ `other-skill`)

## <Context section>
Exactly one of: `## Dataset Reference` | `## Conceptual Framework` | `## Controlled Vocabulary`.
Tables, schemas, file paths, or the enumerated vocabulary the skill depends on.

## Workflow            (or `## Protocol` for step-bound audit skills)
### 1. …
### 2. …
Numbered, ordered steps with code/tool calls where relevant.

## References
- `references/<file>.md` — what it covers
- `scripts/<file>` — what it runs
- External URLs

## Success Criteria
- [ ] Verifiable completion checks
```

**Optional additive sections** (use when the skill type calls for them): - `## Role` — actor framing for audit/review skills ("senior marine biologist", "technical auditor"). - `## Inputs` / `## Outputs` — JSON schemas for skills with a defined I/O contract. - `## Anti-hallucination instruction` — guardrails for evidence-cited audit skills.

------------------------------------------------------------------------

## 4. Controlled taxonomy vocabularies

Choose `domain`, `data-source`, and `output-type` values **only** from these lists. To add a new value, extend the list here in the same PR (the indexer validates against this file's spirit; keep the two in sync). Proposing a genuinely new category is fine — just document it.

**`domain`** — research field / topic:

| Value | Scope |
|------------------------------------|------------------------------------|
| `fisheries-ecology` | Fish populations, biomass, productivity, community structure |
| `reef-ecology` | Coral reef condition, bleaching, benthic cover |
| `biodiversity` | Species richness, diversity indices, occurrence data |
| `biogeography` | Species distributions, range, habitat suitability |
| `oceanography` | Physical/chemical ocean variables (temperature, currents) |
| `climate` | Climate signals, warming, thermal stress, anomalies |
| `conservation-policy` | MPAs, protection effectiveness, management plans, policy |
| `socioeconomics` | Human well-being, prosperity, coastal livelihoods |
| `science-communication` | Briefs, dissemination, publishing, outreach artifacts |
| `meta` | Library infrastructure: skill authoring, tooling, governance |

**`data-source`** — primary data the skill consumes:

| Value           | Scope                                                   |
|-----------------|---------------------------------------------------------|
| `LTEM`          | Baja California Long-Term Ecological Monitoring dataset |
| `OBIS`          | Ocean Biodiversity Information System occurrence data   |
| `ERDDAP`        | ERDDAP gridded/remote-sensing servers (e.g. SST)        |
| `field-survey`  | Direct monitoring/survey data supplied by the user      |
| `PDF-documents` | Management plans, reports, regulations (PDF)            |
| `MPpI`          | Marine Prosperity Index analytical pipeline outputs     |
| `NotebookLM`    | NotebookLM notebooks and Studio artifacts               |
| `generic`       | Source-agnostic / user-provided tabular data            |

**`output-type`** — what the skill produces:

| Value        | Scope                                                       |
|------------------------------------|------------------------------------|
| `analysis`   | Metrics, statistics, exploratory results, figures           |
| `model`      | Fitted models (e.g. species distribution models)            |
| `report`     | Structured human-readable report (markdown/DOCX)            |
| `audit`      | Evidence-cited review/comparison with controlled vocabulary |
| `publishing` | Dissemination artifacts (infographics, audio, slides)       |
| `tooling`    | Repo/library tooling and scaffolding (not a data product)   |

------------------------------------------------------------------------

## 5. Adding a skill — checklist

1.  Copy `TEMPLATE/SKILL.md` to `<your-skill-name>/SKILL.md`.

2.  Fill the frontmatter (§2) and body sections (§3).

3.  Add any `references/`, `scripts/`, or `assets/`.

4.  Run the indexer locally to validate and preview the catalog:

    ``` bash
    python3 tools/build_index.py
    ```

    Fix any validation error it reports (missing field, name mismatch, unknown vocab value).

5.  Commit **only** your skill files. Do **not** commit `INDEX.md`, `catalog.json`, or README table edits — the GitHub Action regenerates them on merge to `main`.

6.  Open a pull request.

------------------------------------------------------------------------

## 6. Output language

Skill **instructions are always written in English.** If a skill's *deliverable* should be produced in another language (e.g. Spanish policy reports for local decision-makers), expose an `output_language` input (default the audience's language) and provide bilingual label sets in a reference guide. See `management-plan-review` and `management-plan-version-comparator` for the pattern.