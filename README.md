# skills

Reusable [Agent Skills](https://agentskills.io) for GlueOps.

These follow the open, vendor-neutral [Agent Skills standard](https://agentskills.io/specification):
a skill is a directory containing a `SKILL.md` (YAML frontmatter + instructions). They are
written to work with **any** skills-compatible AI agent — the instructions use only standard CLI
tools, and the frontmatter uses only standard Agent Skills fields (`name`, `description`, and
`compatibility`), with no vendor-specific extensions.

The repo is also packaged as a Claude Code **plugin** named `glueops`, so Claude Code users get
the skills namespaced as `/glueops:<skill>` (no collisions with their own skills).

## Layout

```
.claude-plugin/
  plugin.json        # packages the repo as the Claude Code plugin "glueops"
  marketplace.json   # lets users `/plugin marketplace add` this repo
skills/
  <skill-name>/
    SKILL.md         # required: `name` + `description` frontmatter, then instructions
    templates/       # optional supporting files, referenced from SKILL.md by relative path
```

## Skills

| Skill | Use it when |
|-------|-------------|
| [release-please](skills/release-please/SKILL.md) | Setting up release-please on a GlueOps repo, **or** reconciling an existing one to the convention (App-token auth, `.yaml`, plain tags, full changelog) — one repo or fleet-wide. |
| [consolidate-dependency-updates](skills/consolidate-dependency-updates/SKILL.md) | Collapsing a repo's open Renovate/Dependabot PRs (any ecosystem) into one validated, release-triggering PR. |

## Install & use

A skill isn't auto-discovered just by living in this repo — **install it once**, then in any
session describe the task (or invoke the skill by name).

### Claude Code (namespaced as `/glueops:<skill>`)

Installing as the `glueops` plugin namespaces the skills so they can't clash with your own.
Two ways:

- **Clone into your personal skills dir** (simplest; auto-loads, `git pull` to update):
  ```bash
  git clone https://github.com/GlueOps/skills ~/.claude/skills/glueops
  ```
  Restart Claude Code — it loads as the plugin `glueops@skills-dir`.
- **Or via the marketplace:**
  ```
  /plugin marketplace add GlueOps/skills
  /plugin install glueops@glueops
  ```

Then describe the task and Claude loads the matching skill, or invoke it directly:
`/glueops:consolidate-dependency-updates`, `/glueops:release-please`.

### GitHub Copilot / other agents

Other agents discover plain skill directories (not the Claude plugin manifest). Copy the skill
directory you want into wherever that agent loads skills — for Copilot that's a repo's
`.github/skills/` or `.claude/skills/`, or your personal `~/.copilot/skills/`:

```bash
git clone https://github.com/GlueOps/skills /tmp/glueops-skills
cp -r /tmp/glueops-skills/skills/consolidate-dependency-updates ~/.copilot/skills/
```

Then describe the task in a session; the agent loads the skill when relevant. (`.claude/skills/`
is read by both Claude Code and Copilot if you prefer a single project-scoped spot.)

### What to say

Describe the goal in plain language; the skill activates on its `description`:
- "Consolidate the open Renovate/Dependabot PRs in `GlueOps/<repo>` into one PR and close the superseded ones."
- "Set up release-please on `GlueOps/<repo>`."

Each skill declares its tool needs in its `compatibility:` field — **consolidate** needs `gh` +
`docker`; **release-please** needs `gh` + `npx`/Node. Make sure `gh` is authenticated.

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for how to author a skill — directory layout,
frontmatter rules, writing a `description` that triggers well, portability, a `SKILL.md`
template, and PR rules. AI agents working in this repo: see **[AGENTS.md](AGENTS.md)**.
