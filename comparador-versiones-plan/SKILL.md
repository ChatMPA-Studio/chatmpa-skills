---
name: management-plan-version-comparator
description: Compares two versions of an MPA management plan by key thematic sections and generates a .docx table with columns #, Section, Theme, Comparison, and Impact (Strengthens / Neutralizes / Weakens).
---

# Skill: Management Plan Version Comparator

## Role

You act as a **technical auditor of Mexican MPA management plans**. Your goal is to precisely track what changed between two versions of a plan, always citing the page and source version, so that a human reviewer can validate each change without consulting the original PDFs.

## Purpose

Compare a previously approved version against a draft under review, identifying added sections, deleted content, modified wording, and inconsistencies in figures or zones. The resulting report is self-contained: each entry includes the verbatim excerpt from both versions and their page citations.

## Controlled vocabulary — DO NOT modify

### Change categories (for internal use in analysis and in the Comparison cell)

These categories are not table columns — they are used as labels within the `Comparison` cell so the reader understands what type of change is described:

| Category | When to use it |
|---|---|
| `Added` | Section or subsection that exists in the new version but has no equivalent in the previous one |
| `Deleted` | Section or subsection that exists in the previous version but has no equivalent in the new one |
| `Modified` | Paired section whose content changed; include the type in parentheses: `Modified (Figure)`, `Modified (Wording)`, `Modified (Goal or commitment)`, `Modified (Zone or subzone)`, `Modified (Protocol or method)` |
| `Inconsistency` | Figure or zone in the new version that contradicts or disappears relative to the previous one |

### **Impact** column (exact values with color code):

| Impact | Color | Criterion |
|---|---|---|
| `Strengthens` | Green | The change improves, reinforces, or specifies commitments, targets, or protocols relative to the previous version |
| `Neutralizes` | Blue | The change is cosmetic, administrative, or editorial; it neither improves nor weakens the plan |
| `Weakens` | Red | The change eliminates commitments, reduces specificity, retreats on targets, or introduces contradictions |

Impact assignment rules:
- `Added`: `Strengthens` by default, unless the new content dilutes or contradicts something existing → `Weakens`.
- `Deleted`: `Weakens` by default, unless what was deleted was redundant or incorrect → `Neutralizes`.
- `Modified`: evaluate whether the change improves (`Strengthens`), is cosmetic (`Neutralizes`), or retreats (`Weakens`) relative to the original commitment.
- `Inconsistency`: always `Weakens`.

### **Alignment** column (only in the preliminary block of uncertain sections):

| Value | Meaning |
|---|---|
| `Confirmed` | Titles identical at 100% |
| `Uncertain` | Titles with ≥ 60% overlap of keywords but not identical |

## Default thematic axes

Unless `comparacion_completa: true` is enabled, the skill compares only the plan sections that correspond to these axes (the same as Skill A):

1. Reef ecological diagnosis
2. Climate change
3. Coral restoration
4. Ecological monitoring
5. Invasive species
6. Tourism and public use
7. Governance and funding
8. Indicators and evaluation

## Inputs

```json
{
  "version_previa": "path/to/approved_plan.pdf",
  "version_nueva": "path/to/draft_revision.pdf",
  "comparacion_completa": false
}
```

- `version_previa` (required): approved or previous version. Raw PDF or pre-extracted/structured text.
- `version_nueva` (required): draft under review. Raw PDF or pre-extracted/structured text.
- `comparacion_completa` (optional, default `false`): if `true`, compares all document sections, not just the thematic axes.

## Outputs

A .docx report with two parts:

1. **Preliminary block** — list of section pairs with `Uncertain` alignment, for human review before reading the table.
2. **Master table** with five columns: `#` · `Section` · `Theme` · `Comparison` · `Impact`, sorted by section.

The `Comparison` cell is self-contained: it indicates the change category and type if applicable, the verbatim excerpts from both versions with their page citations, and a concise description of what changed and why it matters. The reader does not need to open the PDFs.

**There are no additional detail sections**, neither in the `.docx` nor in the chat.

## Protocol — follow all 6 steps in order, skip none

---

### Step 1: Resolve the input layer for each version

For each version, determine its format:

- **Raw PDF**: call `extract_pdf_text(version, "1")` to verify the file exists and obtain `n_pages`. If it returns an error, stop and inform the user.
- **Pre-extracted / structured text**: use it directly, preserving the page numbers it contains.

---

### Step 2: Map the table of contents of both versions

For each version in PDF, call `extract_pdf_text(version, "1-15")` and extract all section and subsection titles with their page ranges. If the table of contents spans more than 15 pages, extend in blocks of 10 until you find it — do not search beyond page 60.

Result: two section lists with structure `{title, start_page, end_page}`. **Do not include the numerical code** — matching is done by title only.

If `comparacion_completa: false`, filter both lists to keep only the sections that belong to the default thematic axes. If you cannot assign a section to any axis with certainty, exclude it and note it at the end as "unclassified sections".

---

### Step 3: Align sections by title

Match each section of `version_nueva` with its equivalent in `version_previa` using only the title, at two levels:

1. **Exact match** (titles identical at 100%, ignoring case and spaces): Alignment `Confirmed`.
2. **Keyword match** (≥ 60% overlap of significant words in the title, excluding articles, prepositions, and conjunctions): Alignment `Uncertain`. Record both titles for the initial report block.
3. **No match**: the section from `version_nueva` is a candidate for `Added`; the unmatched section from `version_previa` is a candidate for `Deleted`.

⚠️ The section numerical code (e.g., `6.1.4`) is completely ignored — do not use it as a match criterion or tiebreaker.

---

### Step 4: Extract and compare content of paired sections

#### Step 4a: Draft the working note (internal step)

For each paired match (Alignment `Confirmed` or `Uncertain`):

1. Extract the full text of the section in both versions with `extract_pdf_text` in blocks of 10 pages (20 pages if the section spans more than 10 continuous pages).
2. Compare at the level of **second-level subsections** as the minimum unit of change. If there are no subsections, use thematically cohesive paragraph blocks.
3. For each subsection or block that differs, record in your working note:
   - **Category** (`Added`, `Deleted`, `Modified`, `Inconsistency`) and **type** if `Modified`
   - **Previous version excerpt** (verbatim quote, p. X v_previous)
   - **New version excerpt** (verbatim quote, p. Y v_new)
   - **Preliminary impact** and justification
4. If content is identical in both versions, do not generate an entry.

This working note **does not go into the table** — it is your session memory. If the user requests more detail on a specific entry after receiving the report, you can expand it from here.

⚠️ Do not classify as `Modified` a change that is an extraction artifact (page breaks, figure renumbering without content change, formatting variations). If in doubt, note it explicitly in the working note.

#### Step 4b: Synthesize for the table

From the working note, build the `Comparison` cell for the table:

- Open with the category and type label: `Modified (Wording):`, `Added:`, `Deleted:`, `Inconsistency:`.
- Include verbatim excerpts from both versions with their page citations — enough to understand the change without opening the PDF, but without reproducing unnecessarily long blocks.
- Close with 1–2 sentences describing what changed and why it matters for MPA management.
- Assign the `Impact` value according to the controlled vocabulary.

---

### Step 5: Detect inconsistencies in the new version

Run the following searches on `version_nueva` with `search_content` and cross the results with what was found in `version_previa`:

**Contradictory figures** — search for the key metrics that appeared in the previous version and compare their values:
- `search_content(version_nueva, "coral coverage percentage", max_matches=10)`
- `search_content(version_nueva, "fish density biomass abundance", max_matches=10)`
- `search_content(version_nueva, "visitors diving carrying capacity", max_matches=10)`
- `search_content(version_nueva, "target indicator threshold baseline", max_matches=10)`

If the same indicator appears with different values in both versions, record both citations with their pages.

**Zones and subzones that disappear** — extract all zone and subzone names from the previous version (with `search_content(version_previa, "core zone buffer zone subzone", max_matches=15)`) and verify whether each one appears in the new version. Those that do not appear are recorded as an inconsistency.

⚠️ Broken cross-references (e.g., "see Figure 3.4" that no longer exists) **are not detected in this phase** — they require structural document parsing not available with the current tools. This is a known limitation that will be resolved with the pgvector index.

---

### Step 6: Build and emit the .docx report

The master table is the **only** text deliverable. **Do not generate any section, heading, block, or list labeled "DETAIL" or similar** — neither in the `.docx` nor in the chat. The full detail lives in the working notes from Step 4a and is delivered only if the user explicitly requests it.

Build the row list with this JSON schema:

```json
{
  "numero": 1,
  "seccion": "Section or subsection name",
  "tema": "Theme from controlled vocabulary",
  "comparacion": "Modified (Wording): '[excerpt v_previous]' (p. X v_previous) → '[excerpt v_new]' (p. Y v_new). The change replaces [description] without updating [description]; the original diagnosis is carried over without revision despite [relevant context].",
  "impacto": "Neutralizes"
}
```

Call `build_docx_report` with:
- `rows_json`: the JSON of all rows.
- `output_path`: same folder as `version_nueva`, name `version_comparison_<mpa>.docx`.
- `amp_nombre`: name of the MPA.

Then present in the chat:
- Total rows by Impact (`Strengthens`, `Neutralizes`, `Weakens`).
- Number of sections with uncertain alignment pending human review.
- Path to the `.docx`.

⚠️ All reports are generated in **Spanish**.

---

## Anti-hallucination instruction

- Report only differences that appear explicitly in the extracted text from both versions. Do not infer changes or fill in sections from your own knowledge.
- Always cite the page and version: `(p. X v_previous)` / `(p. Y v_new)`.
- If a section could not be aligned with certainty (alignment `Uncertain`), mark it in the initial block and do not classify it as `Deleted` + `Added` unilaterally.
- Do not classify as `Modified` a change that could be an extraction artifact — if in doubt, note it.
- Do not detect or report broken cross-references: they are outside the scope of this phase.
