# Contributing a skill

This repo is a library of [Agent Skills](https://agentskills.io) — the open, vendor-neutral
standard (a skill is a directory with a `SKILL.md`). Skills here must work with **any**
skills-compatible AI agent, so keep them portable: standard frontmatter only, neutral
instructions, standard CLI tools.

## Is it a skill?

A skill packages a **repeatable, multi-step procedure** or **specialized knowledge** an agent
executes on demand (e.g. "set up release automation", "consolidate dependency PRs"). If it's a
one-off fact or a single command, it's probably not a skill — it's documentation.

## Add a skill

1. **Create the directory** under `skills/`: `skills/<skill-name>/` — lowercase, hyphenated,
   ≤64 chars. The frontmatter `name` **must match the directory name**. (Skills live under
   `skills/` because the repo is also packaged as the Claude Code plugin `glueops`, which scans
   that directory and namespaces them as `/glueops:<skill-name>`.)
2. **Write `skills/<skill-name>/SKILL.md`** (see the template below).
3. **Put bulky supporting files in a subdirectory** (`templates/`, `scripts/`, `references/`)
   and reference them from `SKILL.md` by relative path. Keep `SKILL.md` focused (rule of thumb:
   under ~500 lines) — this is *progressive disclosure*: the agent loads `SKILL.md` first and
   opens supporting files only when needed.
4. **Add a row** to the Skills table in [`README.md`](README.md).
5. **Open a PR** (see PR rules below).

## `SKILL.md` rules

### Frontmatter — standard fields only

Use only standard Agent Skills fields. **Do not** add vendor-specific extensions
(`disable-model-invocation`, `argument-hint`, `context`, `` !`cmd` `` injection) — only some
agents honor them, which breaks portability. (`allowed-tools` is standard but experimental — use
sparingly.)

| Field | Required | Notes |
|-------|----------|-------|
| `name` | ✅ | lowercase + hyphens, ≤64 chars, matches the directory name |
| `description` | ✅ | ≤1024 chars; **what it does + when to use it** (see below) |
| `compatibility` | optional | tooling/runtime needs, e.g. `Requires git, gh, and docker.` (≤500 chars) |
| `license` | optional | SPDX id or `See LICENSE` |
| `metadata` | optional | arbitrary string key/values |

### Writing a good `description` (this is what triggers the skill)

Agents load only the `name` + `description` at startup and use the description to decide when to
activate the skill. Make it count:
- Lead with the action ("Set up…", "Consolidate…").
- State **when to use it**, including phrasings a user would actually say — even when they don't
  name the tool ("when bot update PRs have piled up").
- Be specific; include real keywords (e.g. `Renovate`, `Dependabot`, `changelog`).
- Don't restate the whole procedure — that's body content, and it just costs matching budget.

### Portable instructions

- Write neutral, **imperative steps** any capable agent can follow. No first-person "I, Claude",
  no harness-specific tool names (Read/Edit/Bash/etc.), no agent-only features.
- Use standard CLI tools (`git`, `gh`, `docker`, language package managers, `jq`, …).
- **Prefer Docker for builds/tests** so a skill is language-agnostic and needs no host toolchain.
- For skills that take **irreversible or outward-facing actions** (closing PRs, deleting files,
  pushing, deploying), put a **human-in-the-loop guard in the body** — both an up-front banner
  and an inline reminder at the destructive step. Don't rely on frontmatter flags for this.

## `SKILL.md` template

```markdown
---
name: my-skill
description: >-
  <Action> a <thing> — <key specifics>. Use when <real user-intent phrasings, including
  cases where the user doesn't name the tool>.
compatibility: Requires <tools>.
---

# My skill

<1–3 sentences: what this does and the outcome.>

> ⚠️ <Only if it has side effects: human-in-the-loop guard.>

## Steps
1. ...
2. ...

## Verify
- [ ] ...
```

## Validate before opening a PR

- `SKILL.md` frontmatter is valid YAML; `name` matches the directory.
- The `description` would trigger at the right time (and not over-trigger).
- Relative links to supporting files resolve.
- A non-Claude agent could follow the steps literally and succeed (walk them).

## PR rules

- **PR title must be a [Conventional Commit](https://www.conventionalcommits.org/)** (e.g.
  `feat: add my-skill`) — CI enforces this.
- CI also runs the org's standard PR checks/labeling; let them pass before merge.
- Keep one skill (or one focused change) per PR.
