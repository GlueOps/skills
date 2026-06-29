# AGENTS.md

Guidance for AI agents working in this repository.

This repo is a library of [Agent Skills](https://agentskills.io) (open, vendor-neutral standard).
When asked to **add or edit a skill**, follow [CONTRIBUTING.md](CONTRIBUTING.md). The essentials:

- One directory per skill under `skills/`: `skills/<skill-name>/SKILL.md`. The frontmatter `name`
  must match the directory name (lowercase, hyphenated). (The repo is packaged as the Claude Code
  plugin `glueops`, which scans `skills/` and namespaces them as `/glueops:<skill-name>`.)
- Frontmatter: standard fields only — `name`, `description`, and optionally `compatibility` /
  `license` / `metadata`. **No vendor-specific fields** (`disable-model-invocation`,
  `argument-hint`, `context`, `` !`cmd` `` injection).
- Keep skills **portable**: neutral imperative instructions, standard CLI tools only, no
  harness-specific tool references. Prefer Docker for builds/tests (language-agnostic).
- Put bulky files in a subdirectory (`templates/`, `scripts/`, …) referenced by relative path;
  keep `SKILL.md` focused.
- For destructive/outward-facing actions, add a human-in-the-loop guard in the body.
- Add the skill to the table in [README.md](README.md).
- **PR titles must be Conventional Commits** (CI enforces this), e.g. `feat: add my-skill`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide and a `SKILL.md` template.
