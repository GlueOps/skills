---
name: consolidate-dependency-updates
description: >-
  Consolidate a repo's piled-up Renovate/Dependabot PRs — dependency bumps (any ecosystem),
  GitHub Actions SHA pins, Dockerfile base-image digests — into one PR that's built and tested in
  Docker, then close the superseded PRs. Use when bot update PRs have accumulated and should ship
  together. Works for any language because all building and testing run in containers.
---

# Consolidate dependency updates (Renovate/Dependabot)

Turn a pile of open bot PRs into **one** green, reviewable PR.

**Requirements:** `git`, `gh` (GitHub CLI), and `docker` (`jq` helpful). Works for **any
ecosystem** — Node, Go, Python, Ruby, Rust, etc. — because all dependency resolution, building,
and testing happen in containers, so the host needs no language toolchains.

> ⚠️ **Run with a human in the loop.** This skill closes other people's PRs and pushes a
> branch/PR. Don't run it autonomously — confirm before closing the superseded PRs, and open the
> consolidated PR for review rather than merging it.

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

## Docker is the test environment (hard rule)

Build and test **only** in containers — never with host toolchains. This is what makes the skill
ecosystem-agnostic: the host needs nothing but `docker`, and each repo's work runs in an image
that carries its own toolchain.
- Prefer the repo's **own `Dockerfile`** (`docker build .`) — it already encodes the correct
  toolchain and is the most faithful check, whatever the language.
- For lockfile regen or running a repo's test command, use a container for that ecosystem
  (`node:*`, `golang:*`, `python:*`, `ruby:*`, `rust:*`, …).
- The Docker daemon may be **remote**, so bind mounts (`-v "$PWD":/app`) won't see your files.
  Use `docker cp` into a running container, or `docker build <dir>` (the build context is uploaded).
- Use the ecosystem's **reproducible/CI install**, not the loose one, for an authoritative result
  (e.g. `npm ci` not `npm install` — the loose install can skip lifecycle scripts; `go mod download`;
  `pip install -r` / `poetry install --sync`).

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
- Package deps: set winning versions in the manifest (`package.json`, `go.mod`,
  `requirements.txt`/`pyproject.toml`, `Gemfile`, `Cargo.toml`, …).
- GitHub Actions: swap each `uses: …@<sha> # vX` to the winning SHA + comment.
- Dockerfile: update the base-image `@sha256:…` digest.

### 4. Regenerate the lockfile in a container (remote daemon → `docker cp`)
Use a container for the repo's ecosystem and run its package manager. Node example:
```bash
CID=$(docker run -d -w /app node:24-alpine sleep 600)
docker cp package.json "$CID":/app/; docker cp package-lock.json "$CID":/app/
docker exec "$CID" sh -c 'cd /app && npm install --no-audit --no-fund'
docker cp "$CID":/app/package-lock.json ./package-lock.json
docker rm -f "$CID"
```
Substitute per ecosystem: `go mod tidy` (golang image), `poetry lock` / `pip-compile` (python),
`bundle lock` (ruby), `cargo update` (rust), etc.

### 5. Validate in Docker — must be green
```bash
docker build -t consolidate-check .          # the repo's own Dockerfile — language-agnostic
```
If the repo has a `Dockerfile`, `docker build .` is the primary check — it exercises the real
toolchain regardless of language. Also run the repo's declared checks/tests in a matching
container (copy the source in, then its lint/test command — `npm ci && npm test`, `go test ./...`,
`pytest`, `bundle exec rspec`, `cargo test`, …). All must pass.

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
