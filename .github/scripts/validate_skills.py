#!/usr/bin/env python3
"""Validate SKILL.md frontmatter for this repo against the Agent Skills standard.

Checks each skills/<name>/SKILL.md:
  - has YAML frontmatter
  - required: name, description
  - name: lowercase + single hyphens, <=64 chars, matches its directory name
  - description: non-empty, <=1024 chars
  - compatibility (optional): string, <=500 chars
  - no vendor-specific frontmatter (keeps skills portable)

Exits non-zero on any violation. Pure-stdlib except PyYAML.
"""
import re
import sys
import pathlib

try:
    import yaml
except ImportError:
    print("pyyaml is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STANDARD_FIELDS = {"name", "description", "compatibility", "license", "metadata", "allowed-tools"}
VENDOR_FIELDS = {"disable-model-invocation", "argument-hint", "context", "disallowed-tools"}

errors = []
warnings = []


def err(skill, msg):
    errors.append(f"{skill}: {msg}")


skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
if not skill_files:
    print(f"No skills found under {SKILLS_DIR.relative_to(ROOT)}/ — nothing to validate.")
    sys.exit(0)

for f in skill_files:
    rel = f.relative_to(ROOT)
    dirname = f.parent.name
    text = f.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        err(rel, "missing YAML frontmatter (--- ... ---) at the top of the file")
        continue
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        err(rel, f"invalid YAML frontmatter: {e}")
        continue
    if not isinstance(fm, dict):
        err(rel, "frontmatter is not a mapping")
        continue

    name = fm.get("name")
    if not name or not isinstance(name, str):
        err(rel, "missing required field: name")
    else:
        if not NAME_RE.match(name):
            err(rel, f"name '{name}' must be lowercase alphanumeric with single hyphens "
                     "(no leading/trailing/consecutive hyphens)")
        if len(name) > 64:
            err(rel, f"name exceeds 64 chars ({len(name)})")
        if name != dirname:
            err(rel, f"name '{name}' must match its directory name '{dirname}'")

    desc = fm.get("description")
    if not desc or not isinstance(desc, str) or not desc.strip():
        err(rel, "missing required field: description")
    elif len(desc) > 1024:
        err(rel, f"description exceeds 1024 chars ({len(desc)})")

    comp = fm.get("compatibility")
    if comp is not None and (not isinstance(comp, str) or len(comp) > 500):
        err(rel, "compatibility must be a string of <=500 chars")

    bad = VENDOR_FIELDS & set(fm.keys())
    if bad:
        err(rel, f"vendor-specific frontmatter not allowed: {', '.join(sorted(bad))} "
                 "(keep skills portable — express that behavior in the body)")

    unknown = set(fm.keys()) - STANDARD_FIELDS - VENDOR_FIELDS
    if unknown:
        warnings.append(f"{rel}: non-standard frontmatter field(s): {', '.join(sorted(unknown))}")

for w in warnings:
    print(f"WARN  {w}")

if errors:
    print("\nSKILL.md validation FAILED:")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)

print(f"✓ validated {len(skill_files)} skill(s): frontmatter OK")
