#!/usr/bin/env python3
"""Emit a ready-to-fill peer-review prompt for a skill.

Reads ``<skill-name>/SKILL.md`` and embeds it in the chatMPA Studio peer-review
rubric (see ``QUALITY.md``). Prints the prompt to stdout — pipe it to a human
reviewer, an LLM judge, or your experiment harness. It performs no network calls
and depends only on the standard library.

Usage::

    python3 tools/review_skill.py ltem-fish-community
    python3 tools/review_skill.py ltem-fish-community | pbcopy
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RUBRIC = """\
You are a peer reviewer for the chatMPA Studio marine-science skills library.
Score the skill below on each dimension from 1 (poor) to 5 (excellent), citing
specific evidence from the skill text. Then give a promotion verdict.

A skill is PROMOTABLE to `stable` only when every dimension scores >= 3 AND
neither Safety nor Scientific validity scores below 4.

Dimensions:
1. Scope & triggering — Is the description specific? Are trigger phrases distinct
   from other skills? Is "when NOT to use" stated?
2. Scientific validity — Are methods, statistics, and aggregation rules correct
   and defensible for the domain? Are assumptions stated?
3. Reproducibility — Are data sources named and paths configurable (not personal)?
   Do referenced scripts/files exist and run? Is output deterministic?
4. Completeness — Are all canonical sections present? Are success criteria
   present and verifiable?
5. Clarity & actionability — Could a non-expert follow the workflow? Are outputs
   decision-ready?
6. Safety — No secrets, destructive operations, or instructions that could
   exfiltrate data or hijack the agent?

Return, in this order:
- A score (1-5) and one-sentence justification for each of the 6 dimensions.
- A list of concrete required changes (if any).
- VERDICT: PROMOTE / REVISE / REJECT, with a one-line reason.

--- SKILL UNDER REVIEW: {name} ---
{skill_text}
--- END SKILL ---
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 tools/review_skill.py <skill-name>", file=sys.stderr)
        return 2
    name = sys.argv[1].rstrip("/")
    skill_md = ROOT / name / "SKILL.md"
    if not skill_md.exists():
        print(f"error: {skill_md.relative_to(ROOT)} not found", file=sys.stderr)
        return 1
    print(RUBRIC.format(name=name, skill_text=skill_md.read_text(encoding="utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
