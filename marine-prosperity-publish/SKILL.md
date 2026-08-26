---
name: marine-prosperity-publish
domain: [conservation-policy, science-communication]
data-source: [NotebookLM]
output-type: [publishing]
tags: [notebooklm, infographic, audio-overview, dissemination]
peer_reviewed: true
status: stable
version: 0.2.0
description: This skill publishes Marine Prosperity Index policy briefs to NotebookLM and produces Studio artifacts (infographic, audio overview, mind map, slide deck). It handles authentication, notebook creation, source ingestion (markdown or DOCX content), and Studio polling. Use this skill when the user asks to "upload the brief to NotebookLM", "generate an infographic", "publish the policy brief", "create an audio overview", or anything that turns an existing MPpI brief into NotebookLM-hosted content. TRIGGER on phrases like "send to NotebookLM", "make an infographic of the brief", "audio overview for <community>", "share the brief as a notebook", or any request that combines an existing policy brief with NotebookLM, infographic, podcast, mind map, or slide deck.
---

# Marine Prosperity Index — NotebookLM Publisher

## Purpose

This skill takes Marine Prosperity Index policy briefs produced by `marine-prosperity-brief` and:

- Uploads each brief to a NotebookLM notebook as a source
- Generates Studio artifacts: infographic, audio overview (podcast), mind map, slide deck
- Polls Studio status until generation completes
- Returns shareable URLs

The skill is a thin orchestration layer over the **notebooklm-mcp** MCP server (`mcp__notebooklm-mcp__*`).

## When to Use This Skill

Use this skill when:
- The user has a `policy_brief_<slug>.md` or `.docx` and wants it on NotebookLM
- The user wants an infographic, podcast (audio overview), mind map, slide deck, flashcards, quiz, or report from a brief
- The user wants to add multiple briefs to one notebook for cross-region synthesis
- The user is preparing assets for a webinar or stakeholder presentation

Do NOT use this skill for:
- Generating the policy brief itself (use `marine-prosperity-brief`)
- Editing the brief content (modify the markdown directly, then re-run brief skill)
- Publishing non-MPpI content (use the notebooklm-mcp tools directly)

## Prerequisites

Before invoking this skill:

1. **A brief exists** at `policy_briefs/policy_brief_<slug>.md` (and optionally a matching DOCX in `policy_briefs/documents_docx/`).
2. **NotebookLM MCP server is connected.** Tool names start with `mcp__notebooklm-mcp__`. If you see `Authentication expired` in the first tool response, ask the user to run:

   ```
   ! notebooklm-mcp-auth
   ```

   in the chat (the `!` prefix runs it inside the session so the browser-auth flow lands its result back in context). `save_auth_tokens` is a fallback only.

3. **Confirm consent for Studio generations.** Tools that produce Studio artifacts (`infographic_create`, `audio_overview_create`, `mind_map_create`, `slide_deck_create`, `video_overview_create`, `report_create`, `flashcards_create`, `quiz_create`, `data_table_create`) require `confirm=True`. Only pass `confirm=True` after the user has explicitly authorized the artifact in this turn.

## Core Workflow

### 1. Decide notebook strategy

| Pattern | When to use |
|---------|-------------|
| **One notebook per brief** | Single-community deep dive; user wants standalone shareable assets |
| **One notebook per region** | Cross-municipality synthesis (e.g. all Gulf of California briefs); enables comparative infographics |
| **Append to existing notebook** | Iterative updates; user gives a notebook UUID or asks to "add Bahía de Kino to the Gulf notebook" |

Check existing notebooks first:

```
mcp__notebooklm-mcp__notebook_list(max_results=50)
```

### 2. Create or open the notebook

```python
# New notebook (per brief)
nb = mcp__notebooklm-mcp__notebook_create(title="Marine Prosperity Index — <Community> Policy Brief")
notebook_id = nb["notebook_id"]   # adapt to actual response shape
```

Naming convention:
- Single brief: `Marine Prosperity Index — <Community> Policy Brief`
- Regional: `Marine Prosperity Index — <Region> Briefs (<Year>)`
- E.g. `Marine Prosperity Index — Gulf of California Briefs (2026)`

### 3. Add the brief as a source

The recommended path is **paste the markdown** (cleaner parsing than DOCX for NotebookLM's chunker):

```python
md = open("policy_briefs/policy_brief_<slug>.md").read()
src = mcp__notebooklm-mcp__notebook_add_text(
    notebook_id=notebook_id,
    title="Policy Brief — <Community>",
    text=md,
)
source_id = src["source_id"]
```

For multi-brief regional notebooks, add each brief as a separate `notebook_add_text` source with the community name in the title — this gives NotebookLM a clean per-source identity for cross-source comparison.

If the brief contains figures the user wants NotebookLM to see, also call `notebook_add_url` pointing at the embedded map (only works if the map is web-accessible). Otherwise rely on the textual metric tables — they're the primary signal NotebookLM uses for infographics.

### 4. Generate Studio artifacts

Confirm the user's intent first, then call the create tool with `confirm=True`. Default knobs for MPpI briefs:

| Artifact | Tool | Recommended args |
|----------|------|------------------|
| Infographic | `infographic_create` | `orientation="landscape"`, `detail_level="standard"`, `language="en"` (or `"es"` for Spanish briefs) |
| Audio overview | `audio_overview_create` | Default; specify `focus_prompt` if the user wants a specific framing (e.g. "frame for policymakers in 7 minutes") |
| Mind map | `mind_map_create` | Default; useful for showcasing the three-axis structure |
| Slide deck | `slide_deck_create` | Default; good for stakeholder webinars |
| Report | `report_create` | When the user wants a longer-form narrative rather than a brief |

Example — infographic generation:

```python
mcp__notebooklm-mcp__infographic_create(
    notebook_id=notebook_id,
    source_ids=[source_id],          # or omit to use all sources
    orientation="landscape",
    detail_level="standard",
    language="en",
    focus_prompt="Highlight Balance, Level, Prosperity (Pp = B × L), the binding constraint, and the four policy scenarios.",
    confirm=True,
)
```

A focus prompt that explicitly mentions **Balance**, **Level**, **Prosperity**, **limiting axis**, and the **four scenarios** dramatically improves infographic quality — NotebookLM otherwise tends to bury those metrics under generic "key findings" framing.

### 5. Poll Studio status

```python
import time
while True:
    s = mcp__notebooklm-mcp__studio_status(notebook_id=notebook_id)
    if all(item["status"] in ("ready", "failed") for item in s["items"]):
        break
    time.sleep(15)
```

In a chatMPA Studio chat session, prefer the Monitor pattern:

```bash
until python3 -c "import json,subprocess,sys; ..."; do sleep 20; done
```

…or simply re-invoke `studio_status` after a wait. Most infographics finish in 60–180 s. Mind maps complete fastest (~30 s). Audio overviews can take 3–8 minutes.

### 6. Return URLs and clean up

Report back to the user:

```
Notebook: <notebook_url>
Infographic: <infographic_url>
Audio overview: <audio_url>
```

If a Studio item failed, surface the error verbatim and ask whether to retry with different `detail_level` or `focus_prompt`. Do not silently retry — generation has a billing cost per attempt.

## Multi-brief Regional Synthesis

When publishing a regional cohort (e.g. all Gulf of California briefs):

1. Create one notebook: `Marine Prosperity Index — Gulf of California Briefs (<Year>)`
2. For each brief, call `notebook_add_text` with `title="Policy Brief — <Community>"`. Capture each `source_id`.
3. Generate one **synthesis infographic** with `source_ids=<all>` and a focus prompt like:
   > "Compare the four prosperity categories across the cohort. Show the regional average vs national average for Balance, Level, and Prosperity. Highlight which communities are limited by Nature vs Livelihood vs Well-being."
4. Optionally also produce **per-community infographics** with `source_ids=[single_source_id]`.

## Handling Failures

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Authentication expired` | OAuth token aged out | `! notebooklm-mcp-auth` |
| `Source too large` | Markdown over the per-source limit | Split brief; or paste only metric tables + recommendations |
| Infographic shows wrong metric names | Generic NotebookLM extraction | Add focus prompt that names B, L, Pp, axes explicitly |
| Studio item stuck at `processing` past 10 min | Backend hiccup | Re-poll once more; if still stuck, retry the create call |

## References

- `references/notebooklm_workflow.md` — Step-by-step examples
- `references/infographic_tips.md` — Focus-prompt patterns for MPpI briefs

## Success Criteria

A successful publish includes:

- [ ] Notebook created with descriptive title
- [ ] Each brief added as a separate text source with named title
- [ ] At least one Studio artifact generated (infographic by default)
- [ ] All Studio items reached `ready` status (no silent failures)
- [ ] Shareable URLs returned to the user
- [ ] Focus prompt explicitly named the MPpI metrics (B, L, Pp, limiting axis, scenarios)
