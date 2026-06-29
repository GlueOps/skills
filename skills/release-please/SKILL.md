---
name: release-please
description: >-
  Set up release automation (release-please) on a GlueOps repo — Conventional-Commit release
  PRs, CHANGELOG, vX.Y.Z tags, and container-image-on-release. Use when adding release
  automation to a repo for the first time.
compatibility: Requires git, gh (GitHub CLI), and npx/Node (for the dry-run).
---

# release-please (GlueOps convention)

release-please reads [Conventional Commits](https://www.conventionalcommits.org/) on `main`,
maintains a "release PR" that bumps the version + updates `CHANGELOG.md`, and on merge cuts a
GitHub release and `vX.Y.Z` tag. This skill is the **GlueOps-standard** greenfield setup, wired
so releases also publish container images.

> ⚠️ **Run with a human in the loop.** This skill deletes a workflow file and opens a PR.
> Don't run it autonomously: confirm before the destructive step (removing the old version-bump
> workflow), and **open the setup PR for review — never push to or merge `main` yourself.**

## Non-negotiables (the convention)

1. **Workflow file:** `.github/workflows/release-please.yaml` — `.yaml`, not `.yml`.
2. **Auth: the `public-release-please` GitHub App**, via `actions/create-github-app-token`.
   Not `GITHUB_TOKEN`, not a PAT (see Why).
3. **Secrets** (org-level, already created): `RELEASE_PLEASE_APP_ID`, `RELEASE_PLEASE_APP_PRIVATE_KEY`.
4. **Manifest mode:** `release-please-config.json` + `.release-please-manifest.json` at repo root.
5. **Plain tags:** `"include-component-in-tag": false` → `vX.Y.Z` (no `reponame-` prefix).

Templates are in [`templates/`](templates/): `release-please.yaml`,
`release-please-config.json`, `.release-please-manifest.json` (already dot-prefixed — copy as-is),
and `container_image.yaml` (optional, see below). The action versions in the templates are
SHA-pinned (with `# vX.Y.Z` comments); refresh them periodically (the
consolidate-dependency-updates skill does this).

## Why the App token

Use the App token from the start: GitHub never triggers other workflows from `GITHUB_TOKEN`
events, so a `GITHUB_TOKEN`-created tag would **not** trigger the image build and release PRs
would **skip required checks**. An App installation token triggers downstream workflows and
lets release PRs run required checks. The App is installed org-wide with exactly
`contents: write`, `pull_requests: write`, `metadata: read` — don't add more.

## ⚠️ Prerequisite: secret visibility

`RELEASE_PLEASE_APP_PRIVATE_KEY` must be readable by the repo. **Most GlueOps repos are
public**, so the org secret's visibility must be **All repositories** (or *Selected* incl. the
repo); otherwise `create-github-app-token` fails. `RELEASE_PLEASE_APP_ID` should already be set
to all.

## Setup

Do all of this on a branch and ship it as one PR — do not commit to `main` directly.

```bash
git clone https://github.com/GlueOps/<repo> && cd <repo>
git checkout -b ci/add-release-please
```

1. **Remove any existing release/version-bump workflow** release-please replaces — most commonly
   `.github/workflows/bump_version.yaml` (the scheduled caller of the shared
   `GlueOps/github-workflows/.../bump-version-cut-release.yaml`). Leaving it in place means **two
   mechanisms creating conflicting tags/releases**. ⚠️ Confirm with a human before deleting.
   ```bash
   git rm .github/workflows/bump_version.yaml   # if present
   ```
2. Copy the templates in. In `release-please-config.json`, set `package-name` and pick
   `release-type`: `node` (Node/SvelteKit), `go` (Go), or `simple` (anything else — tracks
   `version.txt`).
   ```bash
   mkdir -p .github/workflows
   cp <skill>/templates/release-please.yaml          .github/workflows/release-please.yaml
   cp <skill>/templates/release-please-config.json   ./release-please-config.json
   cp <skill>/templates/.release-please-manifest.json ./.release-please-manifest.json
   ```
3. Seed `.release-please-manifest.json` to match the repo's history:
   ```bash
   gh release view --repo GlueOps/<repo> --json tagName -q .tagName 2>/dev/null \
     || git tag --sort=-v:refname | head -1
   ```
   - **No tags** → `{ ".": "0.0.0" }`.
   - **A tag already exists** → seed to that version with `v` stripped (tag `v1.4.2` →
     `{ ".": "1.4.2" }`) so release-please continues from the last tag. The latest tag must be
     plain `vX.Y.Z` to be picked up.
4. Confirm the **secret-visibility** prerequisite above.
5. Commit, push the branch, and open a PR (do **not** merge it yourself):
   ```bash
   git add -A && git commit -m "ci: add release-please"
   git push -u origin ci/add-release-please
   gh pr create --repo GlueOps/<repo> --base main --fill
   ```
6. Optionally run the dry-run (next section) against the pushed branch, then hand the PR to a
   human. **After they merge it**, the next `feat:` (minor) or `fix:` (patch) commit produces a
   release PR; `chore:`/`ci:`/`docs:` do not. Merging that release PR cuts the release + tag.

## Container image publishing (pick one)

If the repo ships a container image, wire the build to the release tag. Both work because the
App-token tag push triggers workflows:

1. **Separate workflow** — copy [`templates/container_image.yaml`](templates/container_image.yaml)
   to `.github/workflows/`. It triggers on `push: tags: ['v*']` and builds the repo's `Dockerfile`
   to `ghcr.io/<org>/<repo>` tagged `vX.Y.Z` + `latest`. Simplest; most repos. (If the repo
   already has an image-build workflow, just make sure it triggers on `push: tags: ['v*']`.)
2. **Inline job** in `release-please.yaml` — add a second job with `needs: release-please` and
   `if: needs.release-please.outputs.release_created == 'true'` that builds/pushes the image
   (tagged with `needs.release-please.outputs.tag_name` + `latest`). Self-contained; works even
   on `GITHUB_TOKEN` since the build runs in the same workflow run.

## Verify

Dry-run reads the config from a **pushed** branch, so push first (step 5), then:

```bash
TOKEN=$(gh auth token)
npx release-please@17 release-pr --token="$TOKEN" \
  --repo-url=GlueOps/<repo> --target-branch=ci/add-release-please --dry-run --debug
```

For a repo with prior releases, confirm it prints `Found release for path ., v<last>` and a sane
candidate version. After the first release tag exists, confirm the image (note: assumes the GHCR
package name matches the repo name):

```bash
gh api /orgs/GlueOps/packages/container/<repo>/versions \
  --jq '.[0].metadata.container.tags'   # expect ["<sha>","v<X.Y.Z>","latest"]
```
