#!/usr/bin/env python3
"""Propagate service-contract skills from chatmpa-skills to downstream repos.

Reads every service-contract SKILL.md (detected by the presence of an 'acquire'
field) from this repo and pushes it — plus any files in references/ — to each
configured downstream GitHub repo via the GitHub API (no local clone needed).

Usage:
    python3 tools/ship.py                               # all skills, all targets
    python3 tools/ship.py --target chatmpa-data-hub     # one target
    python3 tools/ship.py --skill ltem-nrsi-index       # one skill
    python3 tools/ship.py --dry-run                     # print changes, no push
    python3 tools/ship.py --target chatmpa-mvp --dry-run

Requirements:
    - gh CLI authenticated (gh auth status)
    - Run from the chatmpa-skills repo root, or pass --root PATH
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "tools" / "ship_config.json"
NON_SKILL_DIRS = {"TEMPLATE", "tools", ".github"}


# ── helpers ──────────────────────────────────────────────────────────────────

def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def gh_get_file(repo: str, path: str) -> tuple[str, str] | tuple[None, None]:
    """Return (content_str, sha) or (None, None) if file does not exist."""
    try:
        out = gh("api", f"repos/{repo}/contents/{path}", "--jq", ".content + \" \" + .sha")
        parts = out.rsplit(" ", 1)
        content = base64.b64decode(parts[0]).decode("utf-8")
        sha = parts[1]
        return content, sha
    except RuntimeError as e:
        if "404" in str(e) or "Not Found" in str(e):
            return None, None
        raise


def gh_put_file(repo: str, path: str, content: str, sha: str | None, message: str) -> str:
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    cmd = ["api", "--method", "PUT", f"repos/{repo}/contents/{path}",
           "--field", f"message={message}",
           "--field", f"content={encoded}",
           "--jq", ".commit.sha[0:7]"]
    if sha:
        cmd += ["--field", f"sha={sha}"]
    return gh(*cmd)


def is_service_contract(skill_md: Path) -> bool:
    text = skill_md.read_text(encoding="utf-8")
    return bool(re.search(r"^acquire:", text, re.MULTILINE))


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(f"Error: {CONFIG_PATH} not found. Run from chatmpa-skills root.")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def skill_category(name: str, config: dict) -> str | None:
    for cat, skills in config.get("skill_categories", {}).items():
        if name in skills:
            return cat
    return None


def dest_prefix(target_cfg: dict, category: str) -> str:
    prefix = target_cfg.get("prefix", "").rstrip("/")
    return f"{prefix}/{category}" if prefix else category


# ── core propagation ─────────────────────────────────────────────────────────

def ship_skill(skill_dir: Path, target_name: str, target_cfg: dict,
               category: str, dry_run: bool) -> dict[str, str]:
    """Push SKILL.md (and references/*) for one skill to one target repo.
    Returns dict of {path: status} where status is 'updated', 'created', or 'no change'.
    """
    repo = target_cfg["repo"]
    prefix = dest_prefix(target_cfg, category)
    skill_name = skill_dir.name
    results: dict[str, str] = {}

    # Collect files to push: SKILL.md + all files in references/
    files_to_push: list[Path] = [skill_dir / "SKILL.md"]
    refs_dir = skill_dir / "references"
    if refs_dir.is_dir():
        files_to_push.extend(sorted(refs_dir.rglob("*")))

    for local_path in files_to_push:
        if not local_path.is_file():
            continue
        # Relative path within the skill directory
        rel = local_path.relative_to(skill_dir)
        dest_path = f"{prefix}/{skill_name}/{rel}"

        local_content = local_path.read_text(encoding="utf-8")
        remote_content, remote_sha = gh_get_file(repo, dest_path)

        if remote_content == local_content:
            results[dest_path] = "no change"
            continue

        status = "created" if remote_content is None else "updated"
        if dry_run:
            results[dest_path] = f"[dry-run] would be {status}"
            continue

        commit_msg = f"ship({skill_name}): {status} {rel} from chatmpa-skills"
        gh_put_file(repo, dest_path, local_content, remote_sha, commit_msg)
        results[dest_path] = status

    return results


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", metavar="TARGET",
                    help="Propagate to this target only (default: all)")
    ap.add_argument("--skill", metavar="SKILL",
                    help="Propagate this skill only (default: all service-contract skills)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would change without pushing")
    ap.add_argument("--root", metavar="PATH", default=str(ROOT),
                    help="Path to chatmpa-skills repo root (default: auto-detected)")
    args = ap.parse_args()

    config = load_config()

    # Resolve targets
    all_targets = config.get("targets", {})
    if args.target:
        if args.target not in all_targets:
            sys.exit(f"Error: unknown target '{args.target}'. "
                     f"Known: {', '.join(all_targets)}")
        targets = {args.target: all_targets[args.target]}
    else:
        targets = all_targets

    # Collect service-contract skill directories
    root = Path(args.root)
    skill_dirs = sorted(
        d for d in root.iterdir()
        if d.is_dir()
        and d.name not in NON_SKILL_DIRS
        and not d.name.startswith(".")
        and (d / "SKILL.md").exists()
        and is_service_contract(d / "SKILL.md")
    )

    if args.skill:
        skill_dirs = [d for d in skill_dirs if d.name == args.skill]
        if not skill_dirs:
            sys.exit(f"Error: no service-contract skill named '{args.skill}' found.")

    if not skill_dirs:
        print("No service-contract skills found.")
        return 0

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Shipping {len(skill_dirs)} skill(s) "
          f"to {len(targets)} target(s).\n")

    total_updated = total_created = total_nochange = 0

    for skill_dir in skill_dirs:
        name = skill_dir.name
        category = skill_category(name, config)
        if category is None:
            print(f"  ⚠  {name}: not in skill_categories — skipping (add to ship_config.json)")
            continue

        print(f"  {name}  [{category}]")
        for target_name, target_cfg in targets.items():
            results = ship_skill(skill_dir, target_name, target_cfg, category, args.dry_run)
            for path, status in results.items():
                icon = {"updated": "↑", "created": "+", "no change": "·"}.get(
                    status.lstrip("[dry-run] would be "), "?")
                print(f"    {icon} {target_name}: {path}  [{status}]")
                if "updated" in status:
                    total_updated += 1
                elif "created" in status:
                    total_created += 1
                else:
                    total_nochange += 1

    print(f"\nDone. {total_created} created · {total_updated} updated · {total_nochange} unchanged.")
    if args.dry_run:
        print("(dry run — no files were pushed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
