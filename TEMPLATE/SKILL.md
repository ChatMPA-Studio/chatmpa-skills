---
name: my-skill-name
description: >-
  One to three sentences describing what this skill does, who uses it, and the
  trigger phrases that should invoke it. Include a "Do NOT use for…" cross-reference
  to related skills where relevant. Replace this entire block.
domain: [conservation-policy]
data-source: [generic]
output-type: [analysis]
tags: [keyword-one, keyword-two]
status: experimental
version: 0.1.0
# Optional provenance (recommended):
# author: your-name
---

# My Skill Name

## Purpose

Describe who uses this skill, what it does, and what outcomes it produces. Keep it to a
short paragraph plus an optional bullet list of capabilities.

## When to Use This Skill

**Use when:**
- Concrete situation A
- Concrete situation B

**Do NOT use for:**
- Related task X (→ `other-skill`)

## Dataset Reference

> Use exactly one context section here, whichever fits the skill:
> `## Dataset Reference` (data paths/schema) · `## Conceptual Framework` (theory) ·
> `## Controlled Vocabulary` (enumerated allowed values for audit skills).

Describe the data, schema, file paths, or framework the skill depends on. Use tables for
column dictionaries or controlled-vocabulary values.

## Workflow

> Use `## Protocol` instead of `## Workflow` for step-bound audit skills that must run all
> steps in order.

### 1. First step

Explanation, plus a code block or tool call if applicable.

### 2. Second step

…

## References

- `references/<file>.md` — what it covers
- `scripts/<file>` — what it runs
- External: https://…

## Success Criteria

- [ ] Verifiable check 1
- [ ] Verifiable check 2

<!--
Optional additive sections, used when the skill type calls for them:

## Role
Actor framing for audit/review skills (e.g. "senior marine biologist").

## Inputs
```json
{ "param": "value", "output_language": "es" }
```

## Outputs
What the skill emits and where.

## Anti-hallucination instruction
Guardrails for evidence-cited audit skills.
-->
