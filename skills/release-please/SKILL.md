---
name: release-please
description: >-
  Set up release-please on a GlueOps repo, or bring an existing release-please repo up to the
  convention — App-token auth, .yaml workflow, plain vX.Y.Z tags, full changelog, and
  container-image-on-release. Use when adding release automation to a repo, or when an existing
  setup has drifted (GITHUB_TOKEN/PAT, a .yml file, component-prefixed tags, a partial changelog)
  — one repo or fleet-wide.
compatibility: Requires git, gh (GitHub CLI), and npx/Node (for the dry-run).
---

# release-please (GlueOps convention)

release-please reads [Conventional Commits](https://www.conventionalcommits.org/) on `main`,
maintains a "release PR" that bumps the version + updates `CHANGELOG.md`, and on merge cuts a
GitHub release and `vX.Y.Z` tag. This skill brings a repo onto the **GlueOps-standard** release
setup — whether from scratch (**Set up**) or by fixing a drifted one (**Reconcile**) — wired so
releases also publish container images.

> ⚠️ **Run with a human in the loop.** This skill edits/deletes workflow files, may create tags,
> and opens PRs. Don't run it autonomously: confirm before destructive steps (deleting an old
> workflow, creating an anchor tag), and **open PRs for review — never push to or merge `main`.**

## The convention (target state)

1. **Workflow file:** `.github/workflows/release-please.yaml` — `.yaml`, not `.yml`.
2. **Auth: the `public-release-please` GitHub App**, via `actions/create-github-app-token`.
   Not `GITHUB_TOKEN`, not a PAT (see Why).
3. **Secrets** (org-level, already created): `RELEASE_PLEASE_APP_ID`, `RELEASE_PLEASE_APP_PRIVATE_KEY`.
4. **Manifest mode:** `release-please-config.json` + `.release-please-manifest.json` at repo root.
5. **Plain tags:** `"include-component-in-tag": false` → `vX.Y.Z` (no `reponame-` prefix).
6. **Full changelog:** `changelog-sections` lists every Conventional-Commit type (feat, fix, perf,
   revert, docs, style, chore, refactor, test, build, ci, deps). Controls changelog *visibility*
   only — it doesn't change which types cut a release (still feat/fix/breaking).
7. *(0.x repos, optional)* `"bump-minor-pre-major": true` so a breaking change bumps the minor
   instead of jumping to `1.0.0`.
8. If the repo ships an image, its build triggers on `push: tags: ['v*']`.

Templates are in [`templates/`](templates/): `release-please.yaml`, `release-please-config.json`,
`.release-please-manifest.json` (already dot-prefixed — copy as-is), and `container_image.yaml`
(optional). Action versions in the templates are SHA-pinned (`# vX.Y.Z` comments); refresh them
periodically (the consolidate-dependency-updates skill does this).

## Why the App token

GitHub never triggers other workflows from `GITHUB_TOKEN` events, so a `GITHUB_TOKEN`-created tag
would **not** trigger the image build and release PRs would **skip required checks**. An App
installation token triggers downstream workflows and lets release PRs run required checks. The App
is installed org-wide with exactly `contents: write`, `pull_requests: write`, `metadata: read` —
don't add more. (The `CREATE_REPO_RELEASE` PAT fails with "Resource not accessible by personal
access token" — use the App.)

## ⚠️ Prerequisite: secret visibility

`RELEASE_PLEASE_APP_PRIVATE_KEY` must be readable by the repo. **Most GlueOps repos are public**,
so the org secret's visibility must be **All repositories** (or *Selected* incl. the repo);
otherwise `create-github-app-token` fails. `RELEASE_PLEASE_APP_ID` should already be set to all.

---

First pick the path: if the repo has **no** `release-please.y*ml` workflow → **Set up**; if it
already has one (on `GITHUB_TOKEN`/PAT, `.yml`, component tags, or a partial changelog) →
**Reconcile**. Both end in one PR, left for review.

## Set up (new repo)

Do everything on a branch; ship one PR — never commit to `main`.

```bash
git clone https://github.com/GlueOps/<repo> && cd <repo>
git checkout -b ci/add-release-please
```

1. **Remove any existing version-bump workflow** release-please replaces — usually
   `.github/workflows/bump_version.yaml` (the scheduled caller of the shared
   `GlueOps/github-workflows/.../bump-version-cut-release.yaml`). Two mechanisms = conflicting
   tags/releases. ⚠️ Confirm before deleting: `git rm .github/workflows/bump_version.yaml`.
2. Copy the templates in. In `release-please-config.json` set `package-name` and pick
   `release-type`: `node` (Node/SvelteKit), `go` (Go), `helm` (Helm chart — bumps `version` in
   `Chart.yaml`), or `simple` (anything else — tracks `version.txt`). **Don't use `simple` for a
   Helm chart** — it would write a `version.txt` and leave `Chart.yaml` stale.
   ```bash
   mkdir -p .github/workflows
   cp <skill>/templates/release-please.yaml           .github/workflows/release-please.yaml
   cp <skill>/templates/release-please-config.json    ./release-please-config.json
   cp <skill>/templates/.release-please-manifest.json ./.release-please-manifest.json
   ```
3. Seed `.release-please-manifest.json` to the repo's history:
   ```bash
   gh release view --repo GlueOps/<repo> --json tagName -q .tagName 2>/dev/null \
     || git tag --sort=-v:refname | head -1
   ```
   **No tags** → `{ ".": "0.0.0" }`. **A tag exists** → seed to it with `v` stripped (tag `v1.4.2`
   → `{ ".": "1.4.2" }`) so it continues from the last tag (the tag must be plain `vX.Y.Z`).
4. Confirm the **secret-visibility** prerequisite.
5. Commit, push, open a PR (do **not** merge):
   ```bash
   git add -A && git commit -m "ci: add release-please"
   git push -u origin ci/add-release-please && gh pr create --repo GlueOps/<repo> --base main --fill
   ```
6. Verify (below). After a human merges, the next `feat:`/`fix:` produces a release PR; merging
   that cuts the release + tag.

## Reconcile (existing repo)

Bring a drifted setup to *The convention*. On a branch (`ci/reconcile-release-please`):

1. **Inventory** the current state:
   ```bash
   gh api repos/GlueOps/<repo>/contents/.github/workflows --jq '.[].name'
   gh api "repos/GlueOps/<repo>/contents/release-please-config.json" -H "Accept: application/vnd.github.raw"
   gh release view --repo GlueOps/<repo> --json tagName -q .tagName
   ```
   Note: workflow filename (`.yml`/`.yaml`), token in use, `include-component-in-tag`, whether
   `changelog-sections` exists, and the latest tag's **format** (plain `vX.Y.Z` vs `<name>-vX.Y.Z`).
2. **Patch the drift** (each item from *The convention*):
   - rename `release-please.yml` → `.yaml` (`git mv`);
   - insert the `create-github-app-token` step and set `token: ${{ steps.app-token.outputs.token }}`
     (add the `token:` line if absent) — match `templates/release-please.yaml`;
   - add `include-component-in-tag: false`, `changelog-sections`, and (0.x) `bump-minor-pre-major`
     to the config (copy values from `templates/release-please-config.json`; keep the repo's own
     `package-name`, and make sure `release-type` matches the repo — e.g. switch a Helm chart from
     `simple` to `helm` so the version lands in `Chart.yaml`); ensure the manifest exists, seeded
     to the last version;
   - if it has no image-on-tag build, add one (copy `templates/container_image.yaml`).
3. **Tag-format migration — only if switching `<name>-vX.Y.Z` → plain `vX.Y.Z`.** Create an anchor
   tag in the new format at the latest release commit, so release-please finds the baseline instead
   of rescanning all history (which inflates the version and re-lists old commits):
   ```bash
   SHA=$(gh api repos/GlueOps/<repo>/git/ref/tags/<name>-v1.2.3 --jq '.object.sha')   # latest release
   gh api repos/GlueOps/<repo>/git/refs -f ref="refs/tags/v1.2.3" -f sha="$SHA"        # ⚠ confirm first
   ```
4. Confirm secret visibility, commit, push, open **one PR** — do **not** merge.

### Fleet mode (many repos)

To roll the convention across the org: find repos that call `release-please-action` **directly**
by scanning each repo's default-branch workflows for that string (GitHub code search is
capped/lossy — scan authoritatively per repo). **Leave `bump_version.yaml` repos alone** — those
use the shared reusable workflow, a separate mechanism. Reconcile each, open one PR per repo, and
report which were already compliant vs changed.

## Container image publishing (pick one)

Both work because the App-token tag push triggers workflows:

1. **Separate workflow** — copy [`templates/container_image.yaml`](templates/container_image.yaml)
   to `.github/workflows/`; triggers on `push: tags: ['v*']`, builds the `Dockerfile` to
   `ghcr.io/<org>/<repo>` tagged `vX.Y.Z` + `latest`. (If a build workflow already exists, just
   ensure it triggers on `push: tags: ['v*']`.)
2. **Inline job** in `release-please.yaml` — a second job with `needs: release-please` and
   `if: needs.release-please.outputs.release_created == 'true'` that builds/pushes (tagged with
   `needs.release-please.outputs.tag_name` + `latest`). Self-contained.

## Verify

Dry-run reads config from a **pushed** branch, so push first, then:

```bash
TOKEN=$(gh auth token)
npx release-please@17 release-pr --token="$TOKEN" \
  --repo-url=GlueOps/<repo> --target-branch=<your-branch> --dry-run --debug
```

Confirm `Found release for path ., v<last>` and a sane candidate version + clean changelog. After a
release tag exists, confirm the image (assumes the GHCR package name matches the repo):

```bash
gh api /orgs/GlueOps/packages/container/<repo>/versions \
  --jq '.[0].metadata.container.tags'   # expect ["<sha>","v<X.Y.Z>","latest"]
```
