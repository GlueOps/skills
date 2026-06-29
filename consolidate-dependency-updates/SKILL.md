---
name: consolidate-dependency-updates
description: >-
  Consolidate a repo's open Renovate/Dependabot dependency-update PRs into one validated,
  release-triggering PR. Use when bot PRs have piled up — package/npm bumps, GitHub Actions SHA
  pins, Dockerfile base-image digests — and you want them merged together: every bot PR
  attempted, highest version wins, lockfile regenerated and everything built/tested in Docker,
  committed with a release-triggering type (feat/fix, not chore), and superseded PRs closed.
---

# Consolidate dependency updates (Renovate/Dependabot)

Turn a pile of open bot PRs into **one** green, reviewable PR.

## Principles (the decisions)

- **Attempt every open Renovate/Dependabot PR.** Drop one only if it can't be made to build
  after a genuine fix attempt — and document why. Everything else still ships.
- **Highest version wins** when multiple PRs touch the same dep/action/image.
- **One** consolidated PR.
- **Everything builds/tests in Docker** (see below).
- **Release-triggering commit:** commit with a conventional **`feat:`** (default) or `fix:`
  type — **never `chore(deps):`** — so the merge lands as a releasable, changelog-worthy change
  (and triggers a new version in repos that automate releases).
- **Open the PR for review (don't merge); close the superseded PRs.**

## Docker-only (hard rule)

- The host has only the `docker` CLI — no node/npm/etc. Run all lockfile regen, builds, and the
  repo's checks/tests **inside containers** (e.g. `node:24-alpine`).
- The Docker daemon may be **remote**, so bind mounts (`-v "$PWD":/app`) won't see your files.
  Use `docker cp` into a running container, or `docker build <dir>` (the build context is
  uploaded).
- A plain `npm install` in a container can skip lifecycle scripts (npm allow-scripts, e.g.
  esbuild's postinstall) and give misleading failures — use `npm ci` / `docker build` for the
  authoritative result.

## Steps

### 1. Inventory the bot PRs
```bash
gh pr list --repo ORG/REPO --state open --limit 100 \
  --json number,title,headRefName,author,mergeable,isDraft \
  | jq '[.[] | select(.author.is_bot)]'
```
Note: `gh pr list` caps results — page through if there are many. Group by what each touches:
package deps (manifest + lockfile), GitHub Actions pins (`.github/workflows/*`), Docker base
image (`Dockerfile` `FROM …@sha256:`).

### 2. Pick the winning version per item
When several PRs bump the same thing, take the **highest** target. Read exact targets from diffs:
```bash
gh pr diff <n> --repo ORG/REPO | grep -E '^[+-]'
```
For Actions/Docker capture the exact pinned **SHA + version comment**
(`uses: org/action@<sha> # vX.Y.Z`, `FROM image@sha256:<digest>`).

### 3. Build the consolidated branch
```bash
git clone https://github.com/ORG/REPO && cd REPO
git checkout -b chore/consolidate-dependency-updates
```
- Package deps: set winning versions in the manifest (e.g. `package.json`).
- GitHub Actions: swap each `uses: …@<sha> # vX` to the winning SHA + comment.
- Dockerfile: update the base-image `@sha256:…` digest.

### 4. Regenerate the lockfile in Docker (remote daemon → `docker cp`)
```bash
CID=$(docker run -d -w /app node:24-alpine sleep 600)
docker cp package.json "$CID":/app/; docker cp package-lock.json "$CID":/app/
docker exec "$CID" sh -c 'cd /app && npm install --no-audit --no-fund'
docker cp "$CID":/app/package-lock.json ./package-lock.json
docker rm -f "$CID"
```

### 5. Validate in Docker — must be green
```bash
docker build -t consolidate-check .          # the real image build
```
Plus the repo's own checks/tests in a container (cp source into a `node:24-alpine` container,
then `npm ci && npm run check` and any test script). Both must pass.

### 6. Fix breakage first; drop only the unfixable
If validation fails, **try to make every bump work** before giving up on any:
- **Bisect** to the offending bump (revert candidates one at a time; rebuild).
- **Fix it.** Common causes & fixes:
  - needs a **partner bump** (e.g. a plugin's new major requires a newer peer like a bundler) —
    include that bump too;
  - needs a **small code/config change** (e.g. a build-config flag);
  - the absolute-latest is incompatible → use the **highest *compatible*** version instead.
- Only if a bump genuinely can't be made green after a real attempt: **drop just that one**,
  leave its bot PR open, and record the exclusion + reason in the consolidated PR body.
Re-run step 5 until green.

### 7. Open the consolidated PR + close superseded
```bash
git commit -m "feat: consolidate dependency updates"   # release-triggering type, NOT chore
git push -u origin chore/consolidate-dependency-updates
gh pr create --repo ORG/REPO --title "feat: consolidate dependency updates" --body "..."
```
PR body should list: included bumps (with versions), any excluded bumps + reasons, and that
validation passed in Docker. Then close every superseded bot PR with a pointer:
```bash
gh pr close <n> --repo ORG/REPO \
  --comment "Superseded by #<consolidated> (consolidates the open dependency updates)."
```
Leave excluded/unfixable PRs open. **Do not merge** the consolidated PR — leave it for review.

## Verify checklist
- [ ] Every open bot PR is included, or excluded with a documented reason (open).
- [ ] Highest version chosen per item; Action/image SHAs pinned with version comments.
- [ ] `docker build` + the repo's checks/tests pass **in containers**.
- [ ] Commit/PR uses a **release-triggering** type (`feat:`/`fix:`), not `chore`.
- [ ] Superseded PRs closed with a pointer; consolidated PR left unmerged for review.
