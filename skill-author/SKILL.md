---
name: skill-author
description: >-
  Scaffolds, writes, and validates a new chatMPA Studio skill end-to-end, enforcing the
  library's canonical format, taxonomy, quality gates, and no-fabrication rules. Use when
  the user wants to create, add, author, or scaffold a new skill for this repository, or
  asks how to contribute a skill. Do NOT use to run an existing analysis skill, or to edit
  the scientific content of a specific skill — only to create or revise a skill's structure.
domain: [meta]
data-source: [generic]
output-type: [tooling]
tags: [scaffold, authoring, governance, lint, template, versioning]
peer_reviewed: true
status: experimental
version: 0.1.0
author: chatmpa-studio
---

# Skill Author

## Purpose

Guide an author (a human or Claude working inside chatMPA Studio) through creating a new
skill that passes every quality gate on the first try. This skill turns the prose specs in
[`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`QUALITY.md`](../QUALITY.md) into an executable
workflow, so new skills are consistent, discoverable, versioned, and free of the failure
modes we have learned to avoid (broken references, fabricated content, fake scripts,
colliding descriptions).

## When to Use This Skill

**Use when:**
- The user wants to create / add / author / scaffold a new chatMPA skill.
- The user asks how to contribute a skill, or wants an existing draft brought up to the canonical format.

**Do NOT use for:**
- Running an existing skill's analysis (invoke that skill directly).
- Editing the scientific content of one skill (edit that skill's files).
- Repos that are not this skills library.

## Conceptual Framework

A skill is a folder `<skill-name>/` with a required `SKILL.md` plus optional `references/`,
`scripts/`, and `assets/`. `SKILL.md` carries YAML frontmatter (consumed by Claude Code and
the catalog) and a Markdown body (the workflow). The catalog (`INDEX.md`, `catalog.json`,
README table) is generated from frontmatter by `tools/build_index.py` — never edit it by hand.

**Required frontmatter:** `name`, `description`, `domain`, `data-source`, `output-type`,
`tags`, `status`, `version`. **Controlled vocabularies** (pick only these values):

- `domain`: fisheries-ecology, reef-ecology, biodiversity, biogeography, oceanography,
  climate, conservation-policy, socioeconomics, science-communication, meta
- `data-source`: LTEM, OBIS, ERDDAP, field-survey, PDF-documents, MPpI, NotebookLM, generic
- `output-type`: analysis, model, report, audit, publishing, tooling
- `status`: experimental (default for new skills) → stable → deprecated
- `version`: semver `MAJOR.MINOR.PATCH`, start new skills at `0.1.0`

The authoritative vocabulary lives in [`CONTRIBUTING.md`](../CONTRIBUTING.md) §4; if a value
genuinely doesn't fit, extend the vocabulary there and in `tools/build_index.py` in the same change.

## Workflow

### 1. Clarify intent and scope
Ask what the skill should do, who uses it, what data it consumes, and what it produces.
Confirm it isn't already covered by an existing skill (read `catalog.json`).

### 2. Choose a unique kebab-case name
Lowercase-with-hyphens, English, descriptive. It **must equal the folder name**. Verify no
existing folder or `catalog.json` entry already uses it.

### 3. Write a distinct description
1–3 sentences: what it does (active verbs), who uses it, the trigger phrases, and a
"Do NOT use for…" cross-reference. **Check it against every existing description in
`catalog.json`** — overlapping triggers make Claude fire the wrong skill. The linter fails
descriptions whose similarity ≥ 0.70 and warns ≥ 0.40. Keep it under ~700 characters.

### 4. Pick taxonomy
Choose `domain`, `data-source`, `output-type` values from the controlled vocabularies above,
plus free-form lowercase `tags`. Set `status: experimental` and `version: 0.1.0`.

### 5. Scaffold from the template
Copy [`TEMPLATE/SKILL.md`](../TEMPLATE/SKILL.md) to `<skill-name>/SKILL.md` and create
`references/` / `scripts/` only if the skill needs them.

### 6. Fill the canonical body sections
In order: `# Title` → `## Purpose` → `## When to Use This Skill` (use / do-NOT-use) → one
context section (`## Dataset Reference` | `## Conceptual Framework` | `## Controlled
Vocabulary`) → `## Workflow` (or `## Protocol`) with numbered steps → `## References` →
`## Success Criteria`. `## Purpose` and a workflow section are required by the linter; the
others are strongly recommended. Write instructions in **English**; for non-English
deliverables expose an `output_language` input (see `management-plan-review` for the pattern).

### 7. Author references and scripts — the rules that matter most
- **Progressive disclosure:** keep `SKILL.md` lean; put depth in `references/*.md` that
  Claude reads on demand. Every file you point to **must exist** — a broken pointer fails the build.
- **NO FABRICATION:** reference docs contain only established, verifiable domain knowledge.
  Never invent datasets, species lists, study results, numbers, or citations/DOIs. If a
  referenced artifact would be *data you can't produce* (e.g. a real species list), don't
  create a stub — drop the pointer or point to the authoritative source.
- **Real scripts only:** a shipped script must actually run. For anything that hits a live
  external API or downloads data, **do not ship a fake executable** — document the real
  command inline in `SKILL.md` instead.
- **Configurable paths:** never hardcode personal/absolute paths (`/Users/…`, `/home/…`);
  use relative paths or an env var.
- **No secrets:** never commit API keys, tokens, or credentials.

### 8. Validate locally and fix
Run the linter and resolve every error before finishing:
```bash
python3 tools/build_index.py --validate   # errors block; warnings advise
python3 tools/build_index.py              # regenerate the catalog preview
```
Commit only the skill's own files — the catalog is regenerated by CI.

### 9. Hand off to review
New skills ship as `status: experimental`. Generate a peer-review prompt and record the
outcome; promote to `stable` only when it passes the rubric in [`QUALITY.md`](../QUALITY.md):
```bash
python3 tools/review_skill.py <skill-name>
```

## References

- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — authoritative canonical format and vocabularies
- [`QUALITY.md`](../QUALITY.md) — gate model, peer-review rubric, lifecycle, versioning
- [`TEMPLATE/SKILL.md`](../TEMPLATE/SKILL.md) — copyable skeleton
- `tools/build_index.py` — validator + catalog generator (`--validate`, `--check`, `--strict`)
- `tools/review_skill.py` — emits a peer-review prompt for a skill

## Success Criteria

- [ ] Folder name equals `name`; name is unique and kebab-case.
- [ ] All required frontmatter present; taxonomy values are in-vocabulary; `version` is semver; `status: experimental`.
- [ ] Description is specific and not a near-duplicate of any existing skill.
- [ ] Body has `## Purpose` and a workflow section; every referenced file exists.
- [ ] No fabricated content, no fake scripts, no personal paths, no secrets.
- [ ] `python3 tools/build_index.py --validate` passes with zero errors.

## Anti-fabrication rule

This is the single most important rule and the reason this skill exists: **it is always
better to write less that is true than more that is invented.** A reference doc, a number, a
citation, or a script that looks authoritative but is fabricated is worse than its absence —
it will mislead the model and the scientist. When in doubt, omit it or point to the real source.
