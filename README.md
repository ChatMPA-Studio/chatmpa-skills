# chatMPA Skills

A curated library of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills for marine science, developed by the [chatMPA Studio](https://github.com/chatmpa-studio-lab) team.

## What is chatMPA Studio?

**chatMPA Studio** is a marine-science workbench that pairs Claude with domain expertise in oceanography, conservation biology, fisheries science, and marine policy. Its goal is to let scientists, managers, and decision-makers run rigorous analyses and produce decision-ready outputs through natural-language workflows.

This repository is the Studio's **skills library** — a growing, versioned collection of reusable [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) that extend Claude Code with marine-science capabilities: LTEM fish-community analytics, MPA effectiveness assessment, species distribution modeling, sea-surface-temperature workflows, Marine Prosperity Index policy briefs, management-plan audits, and more. Think of it as a CRAN-style catalog: each skill is a self-contained, classified package you can install and invoke on demand.

## Available Skills

<!-- BEGIN SKILLS TABLE -->
| Skill | Version | Status | Domain | Summary |
|---|---|---|---|---|
| [`ltem-biomass-productivity`](./ltem-biomass-productivity/) | 0.2.0 | ✅ stable | fisheries-ecology | This skill analyzes fish biomass, productivity, turnover rates, and environmental drivers using the Baja California LTEM dataset. |
| [`ltem-fish-community`](./ltem-fish-community/) | 0.2.0 | ✅ stable | fisheries-ecology, biodiversity | This skill analyzes fish community structure from the Baja California LTEM (Long-Term Ecological Monitoring) dataset. |
| [`ltem-mpa-effectiveness`](./ltem-mpa-effectiveness/) | 0.2.0 | ✅ stable | conservation-policy, fisheries-ecology | This skill assesses Marine Protected Area effectiveness using the Baja California LTEM dataset. |
| [`ltem-temporal-trends`](./ltem-temporal-trends/) | 0.2.0 | ✅ stable | fisheries-ecology | This skill analyzes temporal trends in fish populations using the 26-year Baja California LTEM dataset (1998-2024). |
| [`management-plan-review`](./management-plan-review/) | 0.2.0 | ✅ stable | conservation-policy, science-communication | Generates a review report for an MPA management plan by cross-referencing its content with scientific evidence to produce a table of concrete recommendations, with action type, confidence level, and APA citations. |
| [`management-plan-version-comparator`](./management-plan-version-comparator/) | 0.2.0 | ✅ stable | conservation-policy | Compares two versions of an MPA management plan by key thematic sections and generates a .docx table with columns #, Section, Theme, Comparison, and Impact (Strengthens / Neutralizes / Weakens). |
| [`marine-prosperity-brief`](./marine-prosperity-brief/) | 0.2.0 | ✅ stable | conservation-policy, socioeconomics | This skill generates Marine Prosperity Index (MPpI) policy briefs for coastal municipalities. |
| [`marine-prosperity-publish`](./marine-prosperity-publish/) | 0.2.0 | ✅ stable | conservation-policy, science-communication | This skill publishes Marine Prosperity Index policy briefs to NotebookLM and produces Studio artifacts (infographic, audio overview, mind map, slide deck). |
| [`marine-species-analysis`](./marine-species-analysis/) | 0.2.0 | ✅ stable | biodiversity, biogeography | This skill should be used when analyzing marine species distributions, accessing OBIS (Ocean Biodiversity Information System) data, building species distribution models (SDMs), or creating marine biodiversity maps. |
| [`mpa-effectiveness-assessment`](./mpa-effectiveness-assessment/) | 0.2.0 | ✅ stable | conservation-policy | This skill should be used when assessing Marine Protected Area (MPA) effectiveness, comparing biodiversity inside vs outside MPAs, analyzing temporal trends in MPA performance, or evaluating conservation outcomes. |
| [`reef-ecology-report`](./reef-ecology-report/) | 0.2.0 | ✅ stable | reef-ecology, biodiversity | This skill should be used when creating reef ecology reports, analyzing coral reef data, or documenting marine ecosystem surveys. |
| [`sea-surface-temperature`](./sea-surface-temperature/) | 0.2.0 | ✅ stable | oceanography, climate | This skill should be used when analyzing sea surface temperature (SST) data, downloading oceanographic data from ERDDAP servers, creating temperature anomaly maps, or studying ocean warming patterns. |
| [`skill-author`](./skill-author/) | 0.1.0 | 🧪 experimental | meta | Scaffolds, writes, and validates a new chatMPA Studio skill end-to-end, enforcing the library's canonical format, taxonomy, quality gates, and no-fabrication rules. |
<!-- END SKILLS TABLE -->

Browse the catalog three ways, all generated from each skill's frontmatter:
- **Interactive catalog** ([`index.html`](./index.html)) — live search, filter chips, and sortable columns. Once GitHub Pages is enabled it is served live (see below); you can also open the file directly in a browser with no server. **Note:** viewing `index.html` on github.com shows its *source* — GitHub never runs repo HTML; it must be served by Pages or opened locally.
- **[`INDEX.md`](./INDEX.md)** — the full catalog grouped into task views (by domain, data source, output type).
- **[`catalog.json`](./catalog.json)** — the machine-readable manifest.

All three are generated automatically — see [Catalog & taxonomy](#catalog--taxonomy).

### Live catalog (GitHub Pages)

The interactive catalog auto-publishes to GitHub Pages on every push to `main` via the *Build skills catalog* workflow. **One-time setup:** in **Settings → Pages**, set **Source: GitHub Actions** (a private repo needs a plan that allows private Pages). The live URL then appears in Settings → Pages and the workflow's `deploy` job — typically `https://chatmpa-studio-lab.github.io/chatmpa-skills/`.

## Installation

Clone this repo into the `.claude/skills/` directory of your project:

```bash
git clone https://github.com/chatmpa-studio-lab/chatmpa-skills .claude/skills
```

Or add it as a git submodule to keep skills in sync:

```bash
git submodule add https://github.com/chatmpa-studio-lab/chatmpa-skills .claude/skills
```

To install only specific skills, use sparse checkout:

```bash
git clone --no-checkout https://github.com/chatmpa-studio-lab/chatmpa-skills .claude/skills
cd .claude/skills
git sparse-checkout init --cone
git sparse-checkout set ltem-mpa-effectiveness marine-prosperity-brief
git checkout main
```

## Updating

```bash
cd .claude/skills && git pull
```

## Skill structure

Each skill follows the Claude Code skill format:

```
<skill-name>/
├── SKILL.md          # Skill definition, triggers, taxonomy, and workflow
├── references/       # Domain reference documents (methodology, guides, context)
├── scripts/          # Helper scripts invoked by the skill
└── assets/           # Templates, logos, fixtures (optional)
```

Only `SKILL.md` is required. Its YAML frontmatter carries the skill `name`, a `description` (with trigger phrases), and the taxonomy fields `domain`, `data-source`, `output-type`, and `tags`.

## Catalog & taxonomy

Every skill is classified along three axes so the library stays searchable as it grows:

- **`domain`** — research field (e.g. `fisheries-ecology`, `oceanography`, `conservation-policy`).
- **`data-source`** — primary data consumed (e.g. `LTEM`, `OBIS`, `ERDDAP`, `PDF-documents`).
- **`output-type`** — what the skill produces (`analysis`, `model`, `report`, `audit`, `publishing`).

These fields drive the catalog. **You never edit the catalog by hand:** the skills table above, [`INDEX.md`](./INDEX.md), and [`catalog.json`](./catalog.json) are regenerated by [`tools/build_index.py`](./tools/build_index.py), which a GitHub Action runs and commits on every push to `main`. Edit a skill's `SKILL.md` frontmatter and the catalog follows.

The controlled vocabularies for each axis are defined in **[`CONTRIBUTING.md`](./CONTRIBUTING.md)**.

## Creating a skill

1. Copy [`TEMPLATE/SKILL.md`](./TEMPLATE/SKILL.md) to `<your-skill-name>/SKILL.md`.
2. Fill in the required frontmatter (`name`, `description`, `domain`, `data-source`, `output-type`, `tags`) and the canonical body sections (Purpose → When to Use → context section → Workflow → References → Success Criteria).
3. Add any `references/`, `scripts/`, or `assets/` your skill needs.
4. Validate and preview the catalog locally:
   ```bash
   python3 tools/build_index.py
   ```
5. Commit only your skill files (not the generated catalog) and open a pull request.

The full canonical format, required components, and contribution checklist live in **[`CONTRIBUTING.md`](./CONTRIBUTING.md)**.

## Quality & governance

Every skill carries a `status` (`experimental` → `stable` → `deprecated`) and passes layered checks before it's trusted: automated structural/security lint and collision detection (`tools/build_index.py`, blocking in CI), then human peer review against a rubric. New skills land as `experimental`; promotion to `stable` requires passing review. See **[`QUALITY.md`](./QUALITY.md)** for the gate model, the peer-review rubric, and the lifecycle policy.

## Related repositories

- [chatmpa-studio](https://github.com/chatmpa-studio-lab/chatmpa-studio) — chatMPA Studio IDE
