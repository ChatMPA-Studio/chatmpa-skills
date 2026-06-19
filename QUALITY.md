# Quality & Governance

How chatMPA Studio keeps skill quality high as the library scales. The goal is **defense in depth**: cheap automation catches the cheap problems, human review catches the rest, and anything that slips through is **reversible** (deprecation/removal) rather than permanent.

No single gate is bulletproof — usefulness and scientific correctness are human judgments. The system is bulletproof in aggregate: a bad skill has to pass *every* layer to reach `stable`.

------------------------------------------------------------------------

## The gate model

| Layer | Gate | Enforced by |
|------------------------|------------------------|------------------------|
| 0 | **Gatekeeping** — no direct pushes to `main`; PR + maintainer review required | Branch protection + [`CODEOWNERS`](./.github/CODEOWNERS) |
| 1 | **Structural lint** — metadata, sections, references, secrets | `tools/build_index.py` (CI, blocking) |
| 2 | **Collision detection** — near-duplicate trigger descriptions | `tools/build_index.py` (CI) |
| 3 | **Security lint** — secrets, risky script idioms | `tools/build_index.py` (CI) |
| 4 | **Peer review** — scientific validity, usefulness | Human reviewer + [rubric](#peer-review-rubric) |
| 5 | **Lifecycle** — experimental → stable → deprecated | `status` frontmatter field |

------------------------------------------------------------------------

## Automated checks

`tools/build_index.py` runs on every PR (`--validate`) and every push to `main`. It has two tiers.

**Errors (block the build):** - Missing/empty required frontmatter (`name`, `description`, `domain`, `data-source`, `output-type`, `tags`, `status`). - `name` not kebab-case, or not equal to the folder name. - Taxonomy or `status` value outside the controlled vocabulary. - Description shorter than 40 chars (placeholder guard). - Missing `## Purpose` or a workflow section (`## Workflow` / `## Core Workflow` / `## Protocol`). - A `references/…`, `scripts/…`, or `assets/…` file mentioned in `SKILL.md` that **does not exist** on disk. - A committed secret (API key, token, private key) in `SKILL.md` or any shipped script. - Two skills with the same `name`. - Two descriptions whose similarity ≥ 0.70 (they would compete for skill selection).

**Warnings (advisory; promote to errors with `--strict`):** - Missing recommended sections (`When to Use`, `References`, `Success Criteria`). - Hardcoded personal paths (`/Users/…`, `/home/…`). - Risky shell idioms in scripts (pipe-to-shell, `rm -rf /`, fork bombs). - Overlong descriptions (\> 700 chars). - Descriptions overlapping ≥ 0.40 similarity. - Non-lowercase tags.

### The ratcheting baseline

Pre-existing errors are recorded once in [`tools/lint_baseline.json`](./tools/lint_baseline.json) and treated as accepted debt, so the build stays green — **but any *new* error still fails.** Quality can only ratchet up.

-   Regenerate after fixing debt (shrinks the baseline): `python3 tools/build_index.py --update-baseline`
-   The current baseline holds known broken-reference debt in the original skills (reference docs/scripts named in `SKILL.md` that were never authored). Address it by either creating the files or removing the dangling mentions, then re-baseline.

Run locally before opening a PR:

``` bash
python3 tools/build_index.py            # regenerate catalog + show warnings
python3 tools/build_index.py --validate  # validation only (what CI runs on PRs)
python3 tools/build_index.py --strict    # fail on warnings too
```

------------------------------------------------------------------------

## Lifecycle (`status`)

Every skill declares a `status`:

| Status | Meaning | In the catalog |
|------------------------|------------------------|------------------------|
| `experimental` | New or unreviewed. Usable but not vetted. **Default for new skills.** | Listed, badged 🧪 |
| `stable` | Passed peer review against the rubric below. | Listed, badged ✅ |
| `deprecated` | Superseded or withdrawn; kept for reference. | Listed, badged ⚠️ |

**Promotion `experimental → stable`** requires: zero lint errors (no new baseline entries), all *recommended* sections present, and a passing peer review (all rubric dimensions ≥ 3, none failing on Safety or Scientific validity).

**Deprecation** is how trash becomes reversible: set `status: deprecated`, add a one-line note in the skill's Purpose pointing to its replacement. Remove the folder only after one release cycle. Users filter on `status`, so deprecating a skill immediately removes it from any "stable-only" install.

------------------------------------------------------------------------

## Versioning & releases

Every skill carries a required `version` (semver `MAJOR.MINOR.PATCH`), so an analysis can be tied to the exact skill that produced it — essential for reproducibility and for the peer-review experiment. New skills start at `0.1.0`. Bump on every meaningful change:

| Change | Bump | Example |
|---|---|---|
| Bug fix, doc/reference tweak, wording | **patch** (`0.2.0 → 0.2.1`) | fix a formula typo in a reference doc |
| New capability, added reference/script, expanded workflow (backward-compatible) | **minor** (`0.2.0 → 0.3.0`) | add a new analysis step or reference |
| Breaking change to inputs, outputs, or behavior; rename | **major** (`0.2.0 → 1.0.0`) | change required input schema |

The catalog (`catalog.json`, `INDEX.md`, README table) surfaces each skill's version. Promotion to `1.0.0` typically coincides with `status: stable`.

**Repo-level releases** track library-wide milestones with git tags (`vMAJOR.MINOR.PATCH`) and a [`CHANGELOG.md`](./CHANGELOG.md) entry. Tag a release after a batch of skill changes lands on `main`:

```bash
git tag -a v0.2.0 -m "chatMPA Skills v0.2.0"
git push origin v0.2.0
```

Users/Studio can pin an exact library state by tag, and an exact skill by its `version`.

------------------------------------------------------------------------

## Peer review

Peer review is the layer automation cannot replace — and the subject of chatMPA Studio's ongoing experiment on whether reviewed skills measurably improve scientific analysis. Each candidate skill is scored by a reviewer (domain expert and/or an LLM judge) against the rubric.

### Peer-review rubric {#peer-review-rubric}

Score each dimension 1–5 (5 = excellent). A skill is **promotable to `stable`** when every dimension scores ≥ 3 and neither *Safety* nor *Scientific validity* scores below 4.

| \# | Dimension | Key questions |
|------------------------|------------------------|------------------------|
| 1 | **Scope & triggering** | Is the description specific? Are the trigger phrases distinct from every other skill? Is "when NOT to use" stated? |
| 2 | **Scientific validity** | Are the methods, statistics, and aggregation rules correct and defensible for the domain? Are assumptions stated? |
| 3 | **Reproducibility** | Are data sources named and paths configurable (not personal)? Do referenced scripts/files exist and run? Is the output deterministic? |
| 4 | **Completeness** | Are all canonical sections present? Do success criteria exist and are they verifiable? |
| 5 | **Clarity & actionability** | Could a non-expert follow the workflow? Are outputs decision-ready? |
| 6 | **Safety** | No secrets, no destructive operations, no instructions that could exfiltrate data or hijack the agent? |

Generate a ready-to-fill review prompt for a skill:

``` bash
python3 tools/review_skill.py <skill-name>
```

Record the outcome in the PR. On promotion, optionally add `reviewed-by:` and bump `version:` in the skill's frontmatter.

------------------------------------------------------------------------

## Branch protection (one-time setup)

Layer 0 is the foundation — without it the automated checks are optional. In the GitHub repo settings, protect `main`:

1.  **Require a pull request before merging**, with **at least 1 approval** and **review from Code Owners**.
2.  **Require status checks to pass** — select the `validate` check from the *Build skills catalog* workflow.
3.  **Restrict who can push** to `main`.

The catalog auto-commit (the `build` job) pushes generated files back to `main`. Either: - **(recommended)** allow the GitHub Actions bot to bypass branch protection for that push, or - switch the `build` job to open a PR instead of pushing directly.

Keep [`.github/CODEOWNERS`](./.github/CODEOWNERS) current so review requests route to the right maintainers.