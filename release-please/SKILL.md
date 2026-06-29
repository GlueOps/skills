---
name: release-please
description: >-
  Set up or fix GitHub release automation (release-please) on a GlueOps repo using the
  public-release-please GitHub App. Use when: adding versioning/changelog/tag automation to
  a repo; switching release-please from GITHUB_TOKEN or the CREATE_REPO_RELEASE PAT to the
  App token; a release PR is stuck/BLOCKED or needs an admin merge; a release was cut but no
  container image was published to GHCR; normalizing the workflow filename to .yaml; or
  changing the tag format (e.g. dropping a component prefix to plain vX.Y.Z).
---

# release-please (GlueOps convention)

release-please reads [Conventional Commits](https://www.conventionalcommits.org/) on `main`,
maintains a "release PR" that bumps the version + updates `CHANGELOG.md`, and on merge cuts a
GitHub release and `vX.Y.Z` tag. This skill encodes the **GlueOps-standard** way to wire it up
so releases also publish container images.

## Non-negotiables (the convention)

1. **Workflow file:** `.github/workflows/release-please.yaml` — `.yaml`, not `.yml`.
2. **Auth: the `public-release-please` GitHub App**, via `actions/create-github-app-token`.
   Do **not** use `GITHUB_TOKEN`. Do **not** use the `CREATE_REPO_RELEASE` PAT (see Why).
3. **Secrets** (org-level, already created): `RELEASE_PLEASE_APP_ID`, `RELEASE_PLEASE_APP_PRIVATE_KEY`.
4. **Manifest mode:** `release-please-config.json` + `.release-please-manifest.json` at repo root.
5. **Plain tags:** `"include-component-in-tag": false` → `vX.Y.Z` (no `reponame-` prefix).

Templates are in [`templates/`](templates/): `release-please.yaml`,
`release-please-config.json`, `release-please-manifest.json` (save the last one as
**`.release-please-manifest.json`** — leading dot).

## Why the App token (do not skip)

| Auth | Result |
|------|--------|
| `GITHUB_TOKEN` | ❌ GitHub never triggers other workflows from `GITHUB_TOKEN` events, so the release **tag does not trigger `container_image.yaml`** (no image) and **release PRs skip required checks** (stuck/BLOCKED → admin merge). |
| `CREATE_REPO_RELEASE` PAT | ❌ Fails: `release-please failed: Resource not accessible by personal access token`. |
| **`public-release-please` App token** | ✅ Triggers downstream workflows (image build) **and** release PRs run required checks (no admin merge). |

The App is installed org-wide with `contents: write`, `pull_requests: write`, `metadata: read`
(release-please's minimal permission set — don't add more).

## ⚠️ Prerequisite: secret visibility (the #1 footgun)

`RELEASE_PLEASE_APP_PRIVATE_KEY` must be readable by the target repo. **Most GlueOps repos are
public**, so the org secret's visibility must be **All repositories** (or *Selected* incl. the
repo). If it's "Private repositories", `create-github-app-token` fails on a public repo.
`RELEASE_PLEASE_APP_ID` should already be "All repositories".

## New repo: setup

1. Add the three files from `templates/` (set `package-name` and pick `release-type`:
   `node` for Node/SvelteKit, `go` for Go, `simple` for everything else — `simple` tracks
   `version.txt`).
2. Seed `.release-please-manifest.json` to `0.0.0` (brand new) or the last released version.
3. Confirm the secret-visibility prerequisite above.
4. Merge. The first `feat:`/`fix:` commit produces a release PR.

## Existing repo: bootstrap "from the last tag"

1. Seed `.release-please-manifest.json` to the **last released version** (e.g. `2.14.1`).
2. Make sure the configured tag format **matches the existing tags**. With
   `include-component-in-tag: false` the expected tag is `vX.Y.Z`. If the latest release tag
   is already `vX.Y.Z`, you're done. If not, see "Changing tag format".
3. **Verify with a dry-run** (below) — it should print `Found release for path ., vX.Y.Z`.

## Switching an existing release-please workflow to the App token

Insert the `create-github-app-token` step before the `release-please-action` step and set
`token: ${{ steps.app-token.outputs.token }}` (add the line if there was none). Rename the
file to `.yaml` if it was `.yml`. See `templates/release-please.yaml` for the end state.

## Changing tag format (e.g. component prefix → plain `vX.Y.Z`)

Single-package repos should use `"include-component-in-tag": false`. **When you change the
format on a repo that already has releases, release-please can no longer find the previous
release under the new name** — it rescans full history, producing a wrong (inflated) version
and a changelog that re-lists already-released commits.

Fix: create an **anchor tag** in the new format at the same commit as the latest release, e.g.
if the latest is `myrepo-v0.1.1`:

```bash
SHA=$(gh api repos/GlueOps/myrepo/git/ref/tags/myrepo-v0.1.1 --jq '.object.sha')
gh api repos/GlueOps/myrepo/git/refs -f ref="refs/tags/v0.1.1" -f sha="$SHA"
```

Then a `fix:` → clean `v0.1.2`, a `feat:` → clean `v0.2.0`. Always confirm with the dry-run.

## Container image publishing (pick one)

Both work because the App-token tag push triggers workflows:

1. **Separate `container_image.yaml`** with `on: push: tags: ['v*']`. Simplest; most repos.
2. **Inline job** in `release-please.yaml`: a second job with
   `needs: release-please` and `if: needs.release-please.outputs.release_created == 'true'`
   that builds/pushes the image (tagged with `needs.release-please.outputs.tag_name` + `latest`).
   Self-contained — works even on `GITHUB_TOKEN` because the build runs in the same workflow run.

## Triggering / forcing a release

- Only releasable commit types bump the version: `feat:` (minor), `fix:` (patch),
  `feat!:`/`BREAKING CHANGE` (major). `chore:`/`ci:`/`docs:` do **not** cut a release.
- **Force a specific version:** add a `Release-As: X.Y.Z` footer to a commit.
- **Empty trigger** (no code change): an empty commit with a `feat:`/`fix:` subject. Create it
  with the Git Data API (PUT contents won't make an empty commit):
  ```bash
  R=GlueOps/myrepo; HEAD=$(gh api repos/$R/git/ref/heads/main --jq .object.sha)
  TREE=$(gh api repos/$R/git/commits/$HEAD --jq .tree.sha)
  printf '{"message":"fix: trigger release","tree":"%s","parents":["%s"]}' "$TREE" "$HEAD" \
    | gh api repos/$R/git/commits --input -
  ```

## Verify

Dry-run before opening/merging (reads config from a branch; `--debug` shows the baseline it found):

```bash
TOKEN=$(gh auth token)
npx release-please@17 release-pr --token="$TOKEN" \
  --repo-url=GlueOps/<repo> --target-branch=<branch> --dry-run --debug
```

Confirm: `Found release for path ., v<last>` and a sane candidate version + clean changelog.

After the release tag exists, confirm the image:

```bash
gh release view --repo GlueOps/<repo> --json tagName
gh api /orgs/GlueOps/packages/container/<repo>/versions \
  --jq '.[0].metadata.container.tags'   # expect ["<sha>","v<X.Y.Z>","latest"]
```

## Troubleshooting

| Symptom | Cause → fix |
|---------|-------------|
| Release PR stuck `BLOCKED`, required check never ran | PR opened by `GITHUB_TOKEN` → switch to App token. One-off: `gh pr merge <n> --squash --admin`. |
| Release cut but no GHCR image | Tag created by `GITHUB_TOKEN`/PAT → switch to App token. |
| `create-github-app-token` step fails | Secret visibility (public repo) or App not installed / wrong perms (needs contents:write + pull_requests:write). |
| `Resource not accessible by personal access token` | Using `CREATE_REPO_RELEASE` PAT → switch to App token. |
| Wrong (inflated) version / changelog re-lists old commits | Tag-format change without an anchor tag → add the anchor (above). |
| No release PR appears | Only `chore`/`ci`/`docs` commits since last release → none are releasable. |

## Rolling out across many repos

- Identify repos that call `release-please-action` **directly** by scanning each repo's default
  branch workflows for the string `release-please-action` (GitHub code search is capped/lossy —
  scan authoritatively per repo).
- **Leave `bump_version.yaml` repos alone** — those call the shared
  `GlueOps/github-workflows/.../bump-version-cut-release.yaml` reusable workflow; they are a
  separate mechanism, not release-please.
