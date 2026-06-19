#!/usr/bin/env python3
"""Build and quality-check the chatMPA Skills catalog.

Scans every top-level ``<skill>/SKILL.md``, validates it against the canonical
format and quality gates (see ``CONTRIBUTING.md`` and ``QUALITY.md``), and
regenerates:

  * ``catalog.json`` — machine-readable manifest (one record per skill)
  * ``INDEX.md``     — human catalog with CRAN-style task views
  * the skills table in ``README.md`` (between the BEGIN/END SKILLS TABLE markers)

Validation has two tiers:
  * ERRORS   — block the build (missing/invalid metadata, broken refs, secrets,
               name collisions, missing core sections, near-duplicate triggers).
  * WARNINGS — advisory signal (missing canonical sections, personal paths,
               risky script idioms, overlong/clashing descriptions). Promote
               them to errors with ``--strict``.

Usage::

    python3 tools/build_index.py            # validate + write the catalog
    python3 tools/build_index.py --check     # validate + fail if outputs are stale
    python3 tools/build_index.py --validate  # validate only (no writes) — for PR checks
    python3 tools/build_index.py --strict     # treat warnings as errors

Standard library only — no third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / "tools" / "lint_baseline.json"

NON_SKILL_DIRS = {"TEMPLATE"}

REQUIRED_FIELDS = ("name", "description", "domain", "data-source", "output-type",
                   "tags", "status", "version")
LIST_FIELDS = ("domain", "data-source", "output-type", "tags")

# Controlled vocabularies — keep in sync with CONTRIBUTING.md §4.
VOCAB = {
    "domain": [
        "fisheries-ecology", "reef-ecology", "biodiversity", "biogeography",
        "oceanography", "climate", "conservation-policy", "socioeconomics",
        "science-communication", "meta",
    ],
    "data-source": [
        "LTEM", "OBIS", "ERDDAP", "field-survey", "PDF-documents", "MPpI",
        "NotebookLM", "generic",
    ],
    "output-type": ["analysis", "model", "report", "audit", "publishing", "tooling"],
}
STATUS_VALUES = ["experimental", "stable", "deprecated"]
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# Tunable quality thresholds.
DESC_MIN_CHARS = 40
DESC_MAX_CHARS = 700
COLLISION_WARN = 0.40
COLLISION_ERROR = 0.70

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY_RE = re.compile(r"^([A-Za-z][\w-]*):\s?(.*)$")
REF_RE = re.compile(r"(?<![\w/])(references|scripts|assets)/[A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9]+")
PERSONAL_PATH_RE = re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+")
SECRET_RES = [
    ("AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("hardcoded api key/secret", re.compile(
        r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9/+_-]{16,}['\"]")),
]
DANGEROUS_SCRIPT_RES = [
    ("pipe-to-shell", re.compile(r"(?:curl|wget)[^\n|]*\|\s*(?:sudo\s+)?(?:ba)?sh")),
    ("rm -rf root", re.compile(r"\brm\s+-rf\s+(?:--no-preserve-root\s+)?/(?:\s|$)")),
    ("base64 pipe shell", re.compile(r"base64\s+-d[^\n|]*\|\s*(?:ba)?sh")),
    ("fork bomb", re.compile(r":\(\)\s*\{\s*:\|:")),
]

AXIS_TITLES = {
    "domain": "By domain (task views)",
    "data-source": "By data source",
    "output-type": "By output type",
}
STATUS_BADGE = {"experimental": "🧪 experimental", "stable": "✅ stable", "deprecated": "⚠️ deprecated"}

TABLE_BEGIN = "<!-- BEGIN SKILLS TABLE -->"
TABLE_END = "<!-- END SKILLS TABLE -->"


# --------------------------------------------------------------------------- #
# Frontmatter parsing
# --------------------------------------------------------------------------- #
def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter dict, body text)."""
    if not text.startswith("---"):
        raise ValueError("file does not start with a YAML frontmatter block")
    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError("unterminated frontmatter block (no closing '---')")

    data: dict = {}
    body = lines[1:end]
    i = 0
    while i < len(body):
        line = body[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = KEY_RE.match(line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest.startswith("[") and rest.endswith("]"):
            items = [x.strip().strip('"').strip("'") for x in rest[1:-1].split(",")]
            data[key] = [x for x in items if x]
        elif rest in (">", ">-", "|", "|-", ">+", "|+", ""):
            folded, j = [], i + 1
            while j < len(body) and (body[j].startswith((" ", "\t")) or not body[j].strip()):
                folded.append(body[j].strip())
                j += 1
            data[key] = " ".join(p for p in folded if p).strip()
            i = j
            continue
        else:
            data[key] = rest.strip().strip('"').strip("'")
        i += 1
    return data, "\n".join(lines[end + 1:])


def h2_headings(body: str) -> list[str]:
    return [ln[3:].strip() for ln in body.splitlines() if ln.startswith("## ")]


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_skills() -> tuple[list[dict], list[str]]:
    skills, load_errors = [], []
    for skill_md in sorted(ROOT.glob("*/SKILL.md")):
        folder = skill_md.parent.name
        if folder in NON_SKILL_DIRS:
            continue
        try:
            fm, body = split_frontmatter(skill_md.read_text(encoding="utf-8"))
        except ValueError as exc:
            load_errors.append(f"{folder}/SKILL.md: {exc}")
            continue
        rec = {
            "name": fm.get("name", folder),
            "description": fm.get("description", ""),
            "domain": fm.get("domain", []),
            "data-source": fm.get("data-source", []),
            "output-type": fm.get("output-type", []),
            "tags": fm.get("tags", []),
            "status": fm.get("status", ""),
            "version": fm.get("version", ""),
            "path": folder,
        }
        if fm.get("author"):
            rec["author"] = fm["author"]
        rec["_fm"] = fm
        rec["_body"] = body
        rec["_dir"] = skill_md.parent
        skills.append(rec)
    return skills, load_errors


# --------------------------------------------------------------------------- #
# Similarity (char trigrams + Jaccard)
# --------------------------------------------------------------------------- #
def trigrams(text: str) -> set[str]:
    norm = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    norm = re.sub(r"\s+", " ", norm)
    return {norm[i:i + 3] for i in range(len(norm) - 2)} if len(norm) >= 3 else {norm}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# --------------------------------------------------------------------------- #
# Ratcheting baseline — pre-existing errors are accepted once, recorded here,
# and NEW errors still fail the build. Regenerate with --update-baseline.
# --------------------------------------------------------------------------- #
def load_baseline() -> set[str]:
    if not BASELINE_PATH.exists():
        return set()
    try:
        data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        return set(data.get("accepted_errors", []))
    except (OSError, json.JSONDecodeError):
        return set()


def write_baseline(errors: list[str]) -> None:
    payload = {
        "_comment": "Pre-existing lint errors accepted as known debt. New errors not listed "
                    "here still fail the build. Regenerate with: "
                    "python3 tools/build_index.py --update-baseline",
        "accepted_errors": sorted(set(errors)),
    }
    BASELINE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate(skills: list[dict]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []

    # Per-skill checks.
    for s in skills:
        sid = f"{s['path']}/SKILL.md"
        fm = s["_fm"]

        for field in REQUIRED_FIELDS:
            if not fm.get(field):
                errors.append(f"{sid}: missing required frontmatter field '{field}'")

        if fm.get("name") and fm["name"] != s["path"]:
            errors.append(f"{sid}: name '{fm['name']}' does not match folder '{s['path']}'")
        if fm.get("name") and not NAME_RE.match(fm["name"]):
            errors.append(f"{sid}: name '{fm['name']}' is not kebab-case")

        for field, allowed in VOCAB.items():
            for value in fm.get(field, []):
                if value not in allowed:
                    errors.append(f"{sid}: invalid {field} value '{value}' "
                                  f"(allowed: {', '.join(allowed)})")
        if s["status"] and s["status"] not in STATUS_VALUES:
            errors.append(f"{sid}: invalid status '{s['status']}' "
                          f"(allowed: {', '.join(STATUS_VALUES)})")
        if s["version"] and not SEMVER_RE.match(str(s["version"])):
            errors.append(f"{sid}: version '{s['version']}' is not semver (MAJOR.MINOR.PATCH)")

        desc = s["description"]
        if desc and len(desc) < DESC_MIN_CHARS:
            errors.append(f"{sid}: description too short ({len(desc)} chars; "
                          f"min {DESC_MIN_CHARS}) — looks like a placeholder")
        if len(desc) > DESC_MAX_CHARS:
            warnings.append(f"{sid}: description is long ({len(desc)} chars; "
                            f"keep under {DESC_MAX_CHARS} for sharp skill selection)")

        for t in s["tags"]:
            if t != t.lower():
                warnings.append(f"{sid}: tag '{t}' should be lowercase")

        # Body sections.
        heads = h2_headings(s["_body"])
        if not any(h == "Purpose" for h in heads):
            errors.append(f"{sid}: missing required '## Purpose' section")
        if not any(h.startswith(("Workflow", "Core Workflow", "Protocol")) for h in heads):
            errors.append(f"{sid}: missing a '## Workflow' / '## Core Workflow' / '## Protocol' section")
        for rec_head, label in (("When to Use", "## When to Use This Skill"),
                                ("References", "## References"),
                                ("Success Criteria", "## Success Criteria")):
            if not any(h.startswith(rec_head) for h in heads):
                warnings.append(f"{sid}: missing recommended section '{label}'")

        # Referenced files must exist.
        for m in REF_RE.finditer(s["_body"]):
            rel = m.group(0)
            if any(c in rel for c in "<>{}*"):
                continue
            if not (s["_dir"] / rel).exists():
                errors.append(f"{sid}: references missing file '{rel}'")

        # Secrets (error) and personal paths (warning).
        full = s["_body"]
        for label, rx in SECRET_RES:
            if rx.search(full):
                errors.append(f"{sid}: possible {label} committed in SKILL.md — remove it")
        n_paths = len(PERSONAL_PATH_RE.findall(full))
        if n_paths:
            warnings.append(f"{sid}: {n_paths} hardcoded personal path(s) (/Users/… or /home/…) "
                            "— use a configurable/relative path")

        # Dangerous idioms in shipped scripts.
        scripts_dir = s["_dir"] / "scripts"
        if scripts_dir.is_dir():
            for script in sorted(scripts_dir.rglob("*")):
                if not script.is_file():
                    continue
                try:
                    content = script.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for label, rx in DANGEROUS_SCRIPT_RES:
                    if rx.search(content):
                        warnings.append(
                            f"{s['path']}/scripts/{script.name}: risky idiom ({label}) — review")
                for label, rx in SECRET_RES:
                    if rx.search(content):
                        errors.append(
                            f"{s['path']}/scripts/{script.name}: possible {label} — remove it")

    # Cross-skill checks.
    seen: dict[str, str] = {}
    for s in skills:
        name = s["name"]
        if name in seen:
            errors.append(f"duplicate skill name '{name}' in {seen[name]} and {s['path']}")
        else:
            seen[name] = s["path"]

    grams = {s["path"]: trigrams(s["description"]) for s in skills}
    for i, a in enumerate(skills):
        for b in skills[i + 1:]:
            sim = jaccard(grams[a["path"]], grams[b["path"]])
            if sim >= COLLISION_ERROR:
                errors.append(f"descriptions of '{a['name']}' and '{b['name']}' are "
                              f"near-duplicates (similarity {sim:.2f} ≥ {COLLISION_ERROR}) — "
                              "they will compete for skill selection; differentiate the triggers")
            elif sim >= COLLISION_WARN:
                warnings.append(f"descriptions of '{a['name']}' and '{b['name']}' overlap "
                                f"(similarity {sim:.2f}) — make trigger phrases more distinct")

    return errors, warnings


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def public_record(s: dict) -> dict:
    return {k: v for k, v in s.items() if not k.startswith("_")}


def first_sentence(text: str) -> str:
    text = text.strip()
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    return (m.group(1) if m else text).strip()


def render_catalog_json(skills: list[dict]) -> str:
    ordered = [public_record(s) for s in sorted(skills, key=lambda s: s["name"])]
    return json.dumps({"count": len(ordered), "skills": ordered}, indent=2, ensure_ascii=False) + "\n"


def render_table_rows(skills: list[dict]) -> str:
    rows = ["| Skill | Version | Status | Domain | Summary |", "|---|---|---|---|---|"]
    for s in sorted(skills, key=lambda s: s["name"]):
        rows.append(
            f"| [`{s['name']}`](./{s['path']}/) | {s['version']} "
            f"| {STATUS_BADGE.get(s['status'], s['status'])} "
            f"| {', '.join(s['domain'])} | {first_sentence(s['description'])} |")
    return "\n".join(rows)


def render_index_md(skills: list[dict]) -> str:
    out = [
        "# chatMPA Skills — Catalog",
        "",
        "> **Auto-generated by `tools/build_index.py`. Do not edit by hand.**",
        "> Regenerated on every push to `main`. To change an entry, edit that skill's "
        "`SKILL.md` frontmatter.",
        "",
        f"**{len(skills)} skills.** Classified along three axes — *domain* (research field), "
        "*data source*, and *output type*. A skill may appear under more than one heading.",
        "",
    ]

    counts = {v: sum(1 for s in skills if s["status"] == v) for v in STATUS_VALUES}
    out.append("**Lifecycle:** " + " · ".join(
        f"{STATUS_BADGE[v]} {counts[v]}" for v in STATUS_VALUES) + ".")
    out.append("")

    for axis in ("domain", "data-source", "output-type"):
        out.append(f"## {AXIS_TITLES[axis]}")
        out.append("")
        for value in VOCAB[axis]:
            members = sorted([s for s in skills if value in s[axis]], key=lambda s: s["name"])
            if not members:
                continue
            out.append(f"### `{value}`")
            out.append("")
            for s in members:
                badge = "" if s["status"] == "stable" else f" — _{s['status']}_"
                out.append(f"- [`{s['name']}`](./{s['path']}/){badge} — {first_sentence(s['description'])}")
            out.append("")

    out.append("## All skills (A–Z)")
    out.append("")
    out.append("| Skill | Version | Status | Domain | Data source | Output | Tags |")
    out.append("|---|---|---|---|---|---|---|")
    for s in sorted(skills, key=lambda s: s["name"]):
        out.append(
            f"| [`{s['name']}`](./{s['path']}/) | {s['version']} "
            f"| {STATUS_BADGE.get(s['status'], s['status'])} "
            f"| {', '.join(s['domain'])} | {', '.join(s['data-source'])} "
            f"| {', '.join(s['output-type'])} | {', '.join(s['tags'])} |")
    out.append("")
    return "\n".join(out)


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>chatMPA Skills — Catalog</title>
<style>
  :root{
    --bg:#0f2233; --panel:#13293d; --line:#244563; --ink:#e8f1f8; --muted:#9bb6cc;
    --accent:#2e8bc0; --chip:#1c3a55; --chipOn:#2e8bc0; --ocean:#0a3d62;
  }
  *{box-sizing:border-box}
  body{margin:0;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:var(--bg);color:var(--ink)}
  header{background:linear-gradient(135deg,#0a3d62,#13293d);padding:24px 28px;border-bottom:1px solid var(--line)}
  h1{margin:0;font-size:22px;letter-spacing:.2px}
  .sub{color:var(--muted);margin-top:4px;font-size:13px}
  main{max-width:1100px;margin:0 auto;padding:20px 28px 60px}
  .toolbar{display:flex;gap:12px;align-items:center;margin:18px 0 8px;flex-wrap:wrap}
  #q{flex:1;min-width:220px;padding:10px 14px;border-radius:10px;border:1px solid var(--line);
    background:var(--panel);color:var(--ink);font-size:15px}
  #q::placeholder{color:var(--muted)}
  .count{color:var(--muted);font-size:13px;white-space:nowrap}
  button.clear{background:var(--chip);border:1px solid var(--line);color:var(--ink);
    padding:9px 12px;border-radius:9px;cursor:pointer;font-size:13px}
  button.clear:hover{border-color:var(--accent)}
  .facets{display:flex;flex-direction:column;gap:8px;margin:10px 0 16px}
  .facet{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
  .facet .lbl{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.6px;min-width:92px}
  .chip{background:var(--chip);border:1px solid var(--line);color:var(--ink);border-radius:999px;
    padding:4px 11px;font-size:12.5px;cursor:pointer;user-select:none}
  .chip:hover{border-color:var(--accent)}
  .chip.on{background:var(--chipOn);border-color:var(--chipOn);color:#fff}
  table{width:100%;border-collapse:collapse;margin-top:8px}
  th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
  th{font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);cursor:pointer;white-space:nowrap}
  th.sortable:hover{color:var(--ink)}
  th .arrow{opacity:.5;font-size:10px}
  td.name a{color:#7fc7ef;text-decoration:none;font-weight:600}
  td.name a:hover{text-decoration:underline}
  .desc{color:var(--muted);font-size:13px;margin-top:3px;max-width:560px}
  .tags{margin-top:5px;display:flex;gap:5px;flex-wrap:wrap}
  .tag{font-size:11px;color:#86a6c2;background:#16304757;border:1px solid var(--line);border-radius:6px;padding:1px 6px}
  .mini{font-size:11.5px;color:var(--muted)}
  .badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;white-space:nowrap;border:1px solid}
  .b-stable{background:#143a2a;border-color:#1f6b46;color:#7fe0ac}
  .b-experimental{background:#3a3414;border-color:#7a6e22;color:#e9d77f}
  .b-deprecated{background:#3a1f14;border-color:#7a3b22;color:#e9a87f}
  .ver{font-variant-numeric:tabular-nums;color:#bcd4e6}
  .empty{padding:40px;text-align:center;color:var(--muted)}
  footer{color:var(--muted);font-size:12px;margin-top:24px;text-align:center}
  a.foot{color:#7fc7ef}
</style>
</head>
<body>
<header>
  <h1>chatMPA Skills</h1>
  <div class="sub">Interactive catalog · <span id="total">__COUNT__</span> skills · auto-generated from <code>catalog.json</code> — do not edit by hand</div>
</header>
<main>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search name, description, tags…" autocomplete="off">
    <span class="count"><span id="shown">0</span> shown</span>
    <button class="clear" id="clear">Clear filters</button>
  </div>
  <div class="facets" id="facets"></div>
  <table>
    <thead><tr>
      <th class="sortable" data-col="name">Skill <span class="arrow"></span></th>
      <th class="sortable" data-col="version">Version <span class="arrow"></span></th>
      <th class="sortable" data-col="status">Status <span class="arrow"></span></th>
      <th>Domain · Source · Output</th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table>
  <div class="empty" id="empty" hidden>No skills match these filters.</div>
  <footer>chatMPA Studio · see <a class="foot" href="./INDEX.md">INDEX.md</a> · <a class="foot" href="./CONTRIBUTING.md">CONTRIBUTING.md</a> · <a class="foot" href="./QUALITY.md">QUALITY.md</a></footer>
</main>
<script>
const SKILLS = __SKILLS_JSON__;
const VOCAB = __VOCAB_JSON__;
const STATUS_ORDER = ["experimental","stable","deprecated"];
const FACETS = [
  {key:"domain", label:"Domain"},
  {key:"data-source", label:"Data source"},
  {key:"output-type", label:"Output"},
  {key:"status", label:"Status"},
];
const sel = {domain:new Set(), "data-source":new Set(), "output-type":new Set(), status:new Set()};
let q = "", sortCol = "name", sortDir = "asc";

function asList(v){ return Array.isArray(v) ? v : [v]; }
function semver(v){ const p=(v||"0.0.0").split(".").map(Number); return (p[0]||0)*1e6+(p[1]||0)*1e3+(p[2]||0); }
function facetValues(key){
  const present = new Set();
  SKILLS.forEach(s => asList(s[key]).forEach(v => present.add(v)));
  const order = VOCAB[key] || (key==="status" ? STATUS_ORDER : null);
  return order ? order.filter(v=>present.has(v)) : [...present].sort();
}
function matches(s){
  if(q){
    const hay = (s.name+" "+s.description+" "+(s.tags||[]).join(" ")).toLowerCase();
    if(!hay.includes(q)) return false;
  }
  for(const key of Object.keys(sel)){
    if(sel[key].size===0) continue;
    if(!asList(s[key]).some(v=>sel[key].has(v))) return false;
  }
  return true;
}
function cmp(a,b){
  let r=0;
  if(sortCol==="version") r = semver(a.version)-semver(b.version);
  else if(sortCol==="status") r = STATUS_ORDER.indexOf(a.status)-STATUS_ORDER.indexOf(b.status);
  else r = a.name.localeCompare(b.name);
  if(r===0) r = a.name.localeCompare(b.name);
  return sortDir==="asc" ? r : -r;
}
function esc(s){ return String(s).replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function buildFacets(){
  const host = document.getElementById("facets");
  host.innerHTML = "";
  FACETS.forEach(f=>{
    const vals = facetValues(f.key);
    if(!vals.length) return;
    const row = document.createElement("div"); row.className="facet";
    row.innerHTML = `<span class="lbl">${f.label}</span>`;
    vals.forEach(v=>{
      const c = document.createElement("span");
      c.className = "chip"+(sel[f.key].has(v)?" on":"");
      c.textContent = v;
      c.onclick = ()=>{ sel[f.key].has(v)?sel[f.key].delete(v):sel[f.key].add(v); buildFacets(); render(); };
      row.appendChild(c);
    });
    host.appendChild(row);
  });
}
function badge(st){ return `<span class="badge b-${esc(st)}">${esc(st)}</span>`; }
function render(){
  const list = SKILLS.filter(matches).sort(cmp);
  const tb = document.getElementById("rows");
  tb.innerHTML = list.map(s=>`
    <tr>
      <td class="name"><a href="./${esc(s.path)}/SKILL.md">${esc(s.name)}</a>
        <div class="desc">${esc(s.description)}</div>
        <div class="tags">${(s.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join("")}</div></td>
      <td class="ver">${esc(s.version||"")}</td>
      <td>${badge(s.status)}</td>
      <td class="mini">${asList(s.domain).join(", ")}<br>${asList(s["data-source"]).join(", ")} · ${asList(s["output-type"]).join(", ")}</td>
    </tr>`).join("");
  document.getElementById("shown").textContent = list.length;
  document.getElementById("empty").hidden = list.length>0;
  document.querySelectorAll("th.sortable").forEach(th=>{
    const a = th.querySelector(".arrow");
    a.textContent = th.dataset.col===sortCol ? (sortDir==="asc"?"▲":"▼") : "";
  });
}
document.getElementById("q").addEventListener("input", e=>{ q=e.target.value.trim().toLowerCase(); render(); });
document.getElementById("clear").addEventListener("click", ()=>{
  q=""; document.getElementById("q").value="";
  Object.values(sel).forEach(s=>s.clear()); buildFacets(); render();
});
document.querySelectorAll("th.sortable").forEach(th=>{
  th.addEventListener("click", ()=>{
    const c=th.dataset.col;
    if(sortCol===c) sortDir = sortDir==="asc"?"desc":"asc"; else { sortCol=c; sortDir="asc"; }
    render();
  });
});
buildFacets(); render();
</script>
</body>
</html>
"""


def render_index_html(skills: list[dict]) -> str:
    data = [public_record(s) for s in sorted(skills, key=lambda s: s["name"])]

    def inline(obj):
        # Escape "<" so an embedded "</script>" can never break out of the tag.
        return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")

    return (HTML_TEMPLATE
            .replace("__SKILLS_JSON__", inline(data))
            .replace("__VOCAB_JSON__", inline(VOCAB))
            .replace("__COUNT__", str(len(data))))


def render_readme(current: str, table: str) -> str | None:
    if TABLE_BEGIN not in current or TABLE_END not in current:
        return None
    pattern = re.compile(re.escape(TABLE_BEGIN) + r".*?" + re.escape(TABLE_END), re.DOTALL)
    return pattern.sub(f"{TABLE_BEGIN}\n{table}\n{TABLE_END}", current)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="validate AND fail if any output is out of date")
    mode.add_argument("--validate", action="store_true",
                      help="validate only (no freshness check, no writes) — for PR checks")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--update-baseline", action="store_true",
                    help="record all current errors as accepted debt in tools/lint_baseline.json")
    args = ap.parse_args()

    skills, load_errors = load_skills()
    errors, warnings = validate(skills) if skills else ([], [])
    errors = load_errors + errors

    if args.update_baseline:
        write_baseline(errors)
        print(f"Baseline updated: {len(set(errors))} accepted error(s) recorded in "
              f"{BASELINE_PATH.relative_to(ROOT)}.")
        return 0

    baseline = load_baseline()
    baselined = [e for e in errors if e in baseline]
    active_errors = [e for e in errors if e not in baseline]
    if args.strict:
        active_errors += [f"(strict) {w}" for w in warnings]

    if warnings:
        print(f"Warnings ({len(warnings)}):\n  - " + "\n  - ".join(warnings), file=sys.stderr)
    if baselined:
        print(f"\nBaselined (known debt, {len(baselined)} — not blocking; "
              f"see tools/lint_baseline.json):\n  - " + "\n  - ".join(baselined), file=sys.stderr)

    if active_errors:
        print(f"\nValidation FAILED ({len(active_errors)} new error(s)):\n  - "
              + "\n  - ".join(active_errors), file=sys.stderr)
        return 1
    if not skills:
        print("No skills found.", file=sys.stderr)
        return 1

    if args.validate:
        print(f"OK — {len(skills)} skills; frontmatter and quality checks passed "
              f"({len(warnings)} warning(s)).")
        return 0

    outputs = {
        ROOT / "catalog.json": render_catalog_json(skills),
        ROOT / "INDEX.md": render_index_md(skills),
        ROOT / "index.html": render_index_html(skills),
    }
    readme_path = ROOT / "README.md"
    readme_status = "no markers"
    if readme_path.exists():
        new_readme = render_readme(readme_path.read_text(encoding="utf-8"), render_table_rows(skills))
        if new_readme is not None:
            outputs[readme_path] = new_readme
            readme_status = "updated"

    stale = [p for p, content in outputs.items()
             if not p.exists() or p.read_text(encoding="utf-8") != content]

    if args.check:
        if stale:
            print("\nOut of date (run `python3 tools/build_index.py`):", file=sys.stderr)
            for p in stale:
                print(f"  - {p.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print(f"OK — {len(skills)} skills; catalog up to date ({len(warnings)} warning(s)).")
        return 0

    for p, content in outputs.items():
        p.write_text(content, encoding="utf-8")
    print(f"Wrote catalog for {len(skills)} skills "
          f"(catalog.json, INDEX.md, README table: {readme_status}); {len(warnings)} warning(s).")
    if readme_status == "no markers":
        print(f"  note: README.md has no {TABLE_BEGIN} / {TABLE_END} markers; table not updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
