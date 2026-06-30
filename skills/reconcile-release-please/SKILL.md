---
name: reconcile-release-please
description: >-
  Bring an existing repo's release-please setup up to the current GlueOps convention — GitHub
  App-token auth, .yaml workflow filename, plain vX.Y.Z tags, and a full changelog. Use when a
  repo already has release-please but has drifted from the standard (still on GITHUB_TOKEN/a PAT,
  a .yml file, component-prefixed tags, or a partial changelog), or to roll the standard across
  many repos at once.
compatibility: Requires git, gh (GitHub CLI), and npx/Node (for the dry-run).
---

# reconcile-release-please (GlueOps convention)

Bring an **existing** release-please repo in line with the GlueOps standard. (For a repo that has
no release-please yet, use the release-please skill instead.)

> ⚠️ **Run with a human in the loop.** This pushes branches/PRs and may create git tags. Confirm
> before creating an anchor tag or opening PRs, and open PRs for review — never push to or merge
> `main` yourself.

## Target state (reconcile each item)

1. Workflow file is `.github/workflows/release-please.yaml` (rename if it's `.yml`).
2. Auth is the `public-release-please` GitHub App via `actions/create-github-app-token` — **not**
   `GITHUB_TOKEN` and **not** a PAT. App tokens trigger the image build and let release PRs run
   required checks; the `CREATE_REPO_RELEASE` PAT fails with "Resource not accessible by personal
   access token".
3. Config is manifest mode: `release-please-config.json` + `.release-please-manifest.json`.
4. `"include-component-in-tag": false` → plain `vX.Y.Z` tags.
5. `"changelog-sections"` lists every Conventional-Commit type (feat, fix, perf, revert, docs,
   style, chore, refactor, test, build, ci, deps) so the full changelog shows.
6. *(0.x repos, optional)* `"bump-minor-pre-major": true` so a breaking change bumps the minor
   instead of jumping to `1.0.0`.
7. If the repo publishes an image, its build triggers on `push: tags: ['v*']`.

Target workflow shape:
```yaml
permissions:
  contents: write
  pull-requests: write
jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0
        id: app-token
        with:
          app-id: ${{ secrets.RELEASE_PLEASE_APP_ID }}
          private-key: ${{ secrets.RELEASE_PLEASE_APP_PRIVATE_KEY }}
      - uses: googleapis/release-please-action@45996ed1f6d02564a971a2fa1b5860e934307cf7 # v5.0.0
        with:
          token: ${{ steps.app-token.outputs.token }}
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json
```

## ⚠️ Prerequisite: secret visibility

`RELEASE_PLEASE_APP_PRIVATE_KEY` must be readable by the repo. **Most GlueOps repos are public**,
so the org secret must be set to **All repositories**; otherwise `create-github-app-token` fails.

## Steps (per repo)

1. **Inventory** the current state:
   ```bash
   gh api repos/GlueOps/<repo>/contents/.github/workflows --jq '.[].name'
   gh api "repos/GlueOps/<repo>/contents/release-please-config.json" -H "Accept: application/vnd.github.raw"
   gh release view --repo GlueOps/<repo> --json tagName -q .tagName
   ```
   Note: the workflow filename (`.yml`/`.yaml`), the token in use, `include-component-in-tag`,
   whether `changelog-sections` exists, and the latest tag's **format** (plain `vX.Y.Z` vs
   `<name>-vX.Y.Z`).
2. **Branch:** `git checkout -b ci/reconcile-release-please`.
3. **Apply the drift fixes** from *Target state*:
   - rename `release-please.yml` → `.yaml` (`git mv`);
   - insert the `create-github-app-token` step and set `token: ${{ steps.app-token.outputs.token }}`
     (add the `token:` line if there was none);
   - add `include-component-in-tag: false`, `changelog-sections`, and (0.x) `bump-minor-pre-major`
     to the config; ensure the manifest exists and is seeded to the last released version.
4. **Tag-format migration — only if switching from `<name>-vX.Y.Z` to plain `vX.Y.Z`.** Create an
   anchor tag in the new format at the same commit as the latest release, so release-please finds
   the baseline instead of rescanning all history (which inflates the version and re-lists old
   commits in the changelog):
   ```bash
   SHA=$(gh api repos/GlueOps/<repo>/git/ref/tags/<name>-v1.2.3 --jq '.object.sha')   # latest release
   gh api repos/GlueOps/<repo>/git/refs -f ref="refs/tags/v1.2.3" -f sha="$SHA"        # ⚠ confirm first
   ```
5. **Commit, push, open one PR** (`ci: reconcile release-please`) — do **not** merge it.

## Verify

Dry-run against the pushed branch (push first):
```bash
TOKEN=$(gh auth token)
npx release-please@17 release-pr --token="$TOKEN" \
  --repo-url=GlueOps/<repo> --target-branch=ci/reconcile-release-please --dry-run --debug
```
Confirm `Found release for path ., v<last>` and a sane candidate version + clean changelog. After
the PR merges, a release tag should trigger the image build — confirm `ghcr.io/.../<repo>:vX.Y.Z`
+ `latest`.

## Fleet mode (many repos)

To roll the standard across the org:
- Find repos that call `release-please-action` **directly**: scan each repo's default-branch
  workflows for the string `release-please-action` (GitHub code search is capped/lossy — scan
  authoritatively per repo).
- **Leave `bump_version.yaml` repos alone** — those call the shared
  `GlueOps/github-workflows/.../bump-version-cut-release.yaml` reusable workflow, a separate
  mechanism, not release-please.
- Reconcile each, open one PR per repo, and report which were already compliant vs changed.

## Verify checklist
- [ ] Workflow is `.yaml` with App-token auth; manifest mode.
- [ ] `include-component-in-tag: false`, `changelog-sections` present, manifest seeded.
- [ ] Anchor tag created **iff** the tag format changed.
- [ ] Dry-run finds the last release + a sane next version.
- [ ] One PR per repo, left unmerged; secret visibility confirmed.
