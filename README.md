# skills

Reusable [Agent Skills](https://agentskills.io) for GlueOps.

These follow the open, vendor-neutral [Agent Skills standard](https://agentskills.io/specification):
a skill is a directory containing a `SKILL.md` (YAML frontmatter + instructions). They are
written to work with **any** skills-compatible AI agent — the instructions use only standard CLI
tools, and the frontmatter uses only standard Agent Skills fields (`name`, `description`, and
`compatibility`), with no vendor-specific extensions.

## Layout

```
<skill-name>/
  SKILL.md     # required: `name` + `description` frontmatter, then instructions
  templates/   # optional supporting files, referenced from SKILL.md by relative path
```

## Skills

| Skill | Use it when |
|-------|-------------|
| [release-please](release-please/SKILL.md) | Setting up release-please (versioning, changelog, tags, container-image publishing) on a GlueOps repo for the first time. |
| [consolidate-dependency-updates](consolidate-dependency-updates/SKILL.md) | Collapsing a repo's open Renovate/Dependabot PRs (any ecosystem) into one validated, release-triggering PR. |

## Use

Skills are consumed however your agent loads them — generically, place (or symlink) the skill
directory into wherever your agent discovers skills, then invoke it by name. Each skill folder
stands on its own (aside from an optional cross-reference link), so you can also copy just the
one you need.

## Contributing

- One directory per skill; the frontmatter `name` must match the directory name (lowercase,
  hyphenated).
- Use only **standard** Agent Skills frontmatter: `name` + `description` (required), and
  optionally `compatibility`, `license`, `metadata`. **Avoid vendor-specific extensions** (e.g.
  `disable-model-invocation`, `argument-hint`, `context`, `` !`cmd` `` injection) — only some
  agents honor them; express that behavior as plain instructions in the body instead.
  (`allowed-tools` is standard but experimental — use sparingly.)
- Write instructions as neutral, imperative steps using standard CLI tools so any capable agent
  can follow them.
- Keep `SKILL.md` focused; push bulky content (templates, scripts, references) into supporting
  files referenced by relative path.
