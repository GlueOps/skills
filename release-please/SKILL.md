---
name: release-please
description: >-
  Set up release automation (release-please) on a GlueOps repo using the public-release-please
  GitHub App. Use when adding versioning, changelog, and vX.Y.Z tagging — plus
  container-image-on-release — to a repo for the first time.
---

# release-please (GlueOps convention)

release-please reads [Conventional Commits](https://www.conventionalcommits.org/) on `main`,
maintains a "release PR" that bumps the version + updates `CHANGELOG.md`, and on merge cuts a
GitHub release and `vX.Y.Z` tag. This skill is the **GlueOps-standard** greenfield setup, wired
so releases also publish container images.

## Non-negotiables (the convention)

1. **Workflow file:** `.github/workflows/release-please.yaml` — `.yaml`, not `.yml`.
2. **Auth: the `public-release-please` GitHub App**, via `actions/create-github-app-token`.
   Not `GITHUB_TOKEN`, not a PAT (see Why).
3. **Secrets** (org-level, already created): `RELEASE_PLEASE_APP_ID`, `RELEASE_PLEASE_APP_PRIVATE_KEY`.
4. **Manifest mode:** `release-please-config.json` + `.release-please-manifest.json` at repo root.
5. **Plain tags:** `"include-component-in-tag": false` → `vX.Y.Z` (no `reponame-` prefix).

Templates are in [`templates/`](templates/): `release-please.yaml`,
`release-please-config.json`, `release-please-manifest.json` (save the last one as
**`.release-please-manifest.json`** — leading dot).

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

1. **Remove any existing release/version-bump workflow** that release-please replaces — most
   commonly `.github/workflows/bump_version.yaml` (the scheduled caller of the shared
   `GlueOps/github-workflows/.../bump-version-cut-release.yaml`). release-please becomes the
   single source of releases; leaving the old one in place means **two mechanisms creating
   conflicting tags/releases**. Delete it in the same PR.
2. Copy the three files from [`templates/`](templates/) into the repo. In
   `release-please-config.json`, set `package-name` and pick `release-type`:
   - `node` — Node / SvelteKit (manages `package.json`)
   - `go` — Go
   - `simple` — anything else (tracks `version.txt`)
3. Seed `.release-please-manifest.json` to match the repo's history. Check for existing tags:
   ```bash
   gh release view --repo GlueOps/<repo> --json tagName -q .tagName 2>/dev/null \
     || git -C <repo> tag --sort=-v:refname | head -1
   ```
   - **No tags** → seed `0.0.0`: `{ ".": "0.0.0" }`.
   - **A tag already exists** → seed to that latest version with the `v` stripped, e.g. tag
     `v1.4.2` → `{ ".": "1.4.2" }`. This makes release-please continue from the last tag
     instead of starting over. (The latest tag must be plain `vX.Y.Z` to be picked up.)
4. Confirm the **secret-visibility** prerequisite above.
5. Merge to `main`. The next `feat:` (minor) or `fix:` (patch) commit produces a release PR;
   `chore:`/`ci:`/`docs:` do not. Merging the release PR cuts the release + tag.

## Container image publishing (pick one)

Both work because the App-token tag push triggers workflows:

1. **Separate `container_image.yaml`** with `on: push: tags: ['v*']`. Simplest; most repos.
2. **Inline job** in `release-please.yaml`: a second job with `needs: release-please` and
   `if: needs.release-please.outputs.release_created == 'true'` that builds/pushes the image
   (tagged with `needs.release-please.outputs.tag_name` + `latest`). Self-contained.

## Verify

Dry-run before merging the setup (reads config from a branch; `--debug` shows what it found):

```bash
TOKEN=$(gh auth token)
npx release-please@17 release-pr --token="$TOKEN" \
  --repo-url=GlueOps/<repo> --target-branch=<branch> --dry-run --debug
```

For a repo with prior releases, confirm it prints `Found release for path ., v<last>` and a
sane candidate version. After the first release tag exists, confirm the image:

```bash
gh api /orgs/GlueOps/packages/container/<repo>/versions \
  --jq '.[0].metadata.container.tags'   # expect ["<sha>","v<X.Y.Z>","latest"]
```
