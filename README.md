# skills

Reusable [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) for GlueOps.

## Layout

Each skill is a directory with a `SKILL.md` (YAML frontmatter `name` + `description`, then
instructions). Supporting files (templates, scripts) live alongside it and are referenced from
`SKILL.md` by relative path.

```
<skill-name>/
  SKILL.md
  templates/   # optional supporting files
```

## Skills

| Skill | Use it when |
|-------|-------------|
| [release-please](release-please/SKILL.md) | Setting up or fixing release-please (versioning, changelog, tags, container-image publishing) on a GlueOps repo. |
