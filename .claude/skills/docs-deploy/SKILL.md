---
name: docs-deploy
description: Update and deploy the Weaverlet docs site at https://weaverlet.observatoriogeo.mx via the GitHub Pages workflow (.github/workflows/docs-deploy.yml). Use whenever the user wants to deploy, redeploy, ship, push, publish, or update the docs site to production / Pages / live, AND whenever the user wants to check whether the deploy is in sync ("is everything synced?", "did my docs changes ship?", "is local in sync with the published site?", "is the docs site up to date with main?"). Triggers on deploy phrases like "deploy the docs", "redeploy", "publish the website", "ship the docs", "update the live site", any mention of weaverlet.observatoriogeo.mx; AND on sync-check phrases like "is everything synced", "verify the deploy", "did my changes ship".
---

# Docs deploy workflow (Weaverlet)

End-to-end loop for publishing the Weaverlet documentation site to GitHub Pages on the vanity domain `https://weaverlet.observatoriogeo.mx`. The deploy is a single GitHub Actions workflow; there is no SSH, no Jinja2 templating, no reverse-proxy chain. Pushes to `main` that touch `website/**` (or the workflow file itself) build and publish; nothing else triggers a deploy.

## Fixed parameters for this project

These do not change across deploys. If the user asks to deploy somewhere else, stop and ask, do not silently swap a value.

| Param | Value | Where |
|---|---|---|
| Repo (SSH) | `git@github.com:observatoriogeo/weaverlet.git` | |
| Default branch | `main` | |
| Workflow | `.github/workflows/docs-deploy.yml` (jobs: `build`, `deploy`) | |
| Build path | `website/` | |
| Build cmd | `cd website && npm ci && npm run build` | |
| Lock file (must be tracked) | `website/package-lock.json` | exempted in root `.gitignore` |
| Node version | 20 (pinned by `actions/setup-node@v4`) | workflow |
| Custom domain | `weaverlet.observatoriogeo.mx` | `website/static/CNAME` |
| DNS record | `CNAME weaverlet.observatoriogeo.mx. -> observatoriogeo.github.io.` | observatoriogeo.mx zone (out of repo scope) |
| Pages config | `build_type: workflow`, `cname: weaverlet.observatoriogeo.mx`, `https_enforced: true` | repo Settings → Pages |
| Workflow trigger paths | `website/**`, `.github/workflows/docs-deploy.yml` | workflow `on.push.paths` |
| Site config | TypeScript: `website/docusaurus.config.ts` (not `.js`) | |
| Versioning | `lastVersion: '0.3.1'`; `versioned_docs/version-0.3.1/` is the published snapshot, `docs/` is the "next" version | |

## Architecture (so you can debug when something does not deploy)

```
git push main
     │  (only if paths under website/** or the workflow file changed)
     ▼
.github/workflows/docs-deploy.yml
     ├─ build:  actions/checkout → setup-node@20 (cache: website/package-lock.json)
     │          → npm ci (in website/) → npm run build → upload-pages-artifact
     └─ deploy: actions/deploy-pages → Pages serves at weaverlet.observatoriogeo.mx
```

Typical timing is ~2 min build + ~10 s deploy (longer than a flat docs site — Weaverlet builds two versions: `next` from `docs/` and the snapshotted `0.3.1` from `versioned_docs/`). The two jobs run sequentially; the deploy job depends on the build artifact.

## Content model

Docs are hand-written `.mdx` files (MDX 3) under `website/docs/` (the working "next" version) and `website/versioned_docs/version-0.3.1/` (the published 0.3.1 snapshot). There is no sync script — what's in those trees is what gets published. The sidebar for each version lives in `website/sidebars.ts` (next) and `website/versioned_sidebars/version-0.3.1-sidebars.json` (frozen at version-cut time).

Static assets live in `website/static/`. The custom domain pin is `website/static/CNAME` (single line: `weaverlet.observatoriogeo.mx`). Logo and favicon at `website/static/img/`. The `baseUrl: '/'` in `docusaurus.config.ts` is load-bearing for the custom-domain deploy.

## Working with versioned docs

Two versions ship: `next` (from `website/docs/`) and `0.3.1` (snapshotted under `website/versioned_docs/version-0.3.1/`).

- **Edits to the live published docs** → edit `website/versioned_docs/version-0.3.1/`. Those land at `/docs/...` (the `lastVersion` serves at `/docs/` directly).
- **Edits to the unreleased "next" docs** → edit `website/docs/`. Those land at `/docs/next/...` once a *second* version is snapshotted (until then, `next` and `last` are the same content so a second version does not appear in the dropdown — see `docusaurus.config.ts`'s `lastVersion` + `versions` map).
- **Cutting a new version** (e.g., for a 0.4.0 release):
  ```bash
  cd website && npm run docusaurus docs:version 0.4.0
  ```
  Then update `docusaurus.config.ts`: set `lastVersion: '0.4.0'`, add `'0.4.0': {label: '0.4.0'}` to the `versions:` map, and decide what label `0.3.1` should carry going forward (typically `'0.3.1'`). The `versions.json` file at `website/versions.json` is auto-updated by the `docs:version` command — you should not edit it by hand.
- **Sidebars** for old versions are frozen — if you need to change the 0.3.1 sidebar shape, edit `versioned_sidebars/version-0.3.1-sidebars.json` directly. Live sidebar edits to `sidebars.ts` only affect the `next` version.

Common mistake: editing `website/docs/some-page.mdx` and expecting it to appear at `/docs/some-page` immediately. Because `lastVersion: '0.3.1'` is set, `/docs/some-page` serves the 0.3.1 snapshot. Cross-check by editing `website/versioned_docs/version-0.3.1/some-page.mdx` if the goal is to update the live page right now.

## Phases (the deploy loop)

Four phases for an active deploy. Phase 5 is a standalone sync check (no deploy in progress).

### 1. Local build verification

```bash
cd website && npm run build
```

`onBrokenLinks: 'throw'` is set in `docusaurus.config.ts`, so any broken internal link fails the build hard. Do not push if the build fails — the workflow will reproduce the same failure and the Pages deploy will be skipped.

Common build-breakers:

- **Trailing-slash drift on directory-index docs.** This is the most likely build-time and runtime failure mode (see Failure Mode #1 below) — read it before touching `docusaurus.config.ts` or the homepage / footer hardcoded `to:` props.
- HTML comments `<!-- -->` in `.mdx` files — MDX 3 strict parsing fails on these. Use `{/* ... */}` instead.
- A sidebar or navbar entry pointing at a doc that has been renamed or deleted.
- A relative MDX link `[text](./missing)` where `missing.mdx` no longer exists in the same directory.

### 2. Commit and push

```bash
git add <paths>
git status
git commit -m "<one-line summary>"
git push origin main
```

Before committing, confirm `website/package-lock.json` is in the diff if `package.json` changed. Pushing is visible to others and triggers the live deploy, so confirm with the user unless they have already said "deploy".

If the changes touch only paths outside `website/**` (for example `weaverlet/`, `examples/`, `tests/`), the push will NOT trigger a deploy. To force a redeploy with no content change:

```bash
gh workflow run docs-deploy.yml --ref main
```

### 3. Watch the workflow

```bash
RUN_ID=$(gh run list --workflow=docs-deploy.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --exit-status
```

Typical timing: ~2 min build, ~10 s deploy. If the build step fails, view the logs with `gh run view "$RUN_ID" --log-failed`.

### 4. Verify live

Three-line smoke test against the public URL:

```bash
# Root
curl -sS -o /dev/null -w 'root:    %{http_code}\n' \
  https://weaverlet.observatoriogeo.mx/

# Single-page doc (catches baseUrl misconfig)
curl -sS -o /dev/null -w 'quick:   %{http_code}\n' \
  https://weaverlet.observatoriogeo.mx/docs/quickstart

# Directory-index doc (catches trailing-slash drift and sidebar breakage)
curl -sS -o /dev/null -w 'api:     %{http_code}\n' \
  https://weaverlet.observatoriogeo.mx/docs/api/
```

All three should return 200 (a 301 on the no-slash form `/docs/api` is fine — Pages emits a trailing-slash redirect for directory-style URLs). If any return 404 or SSL errors, jump to "Debugging unreachable deploys" below.

Also grep the root HTML for `<meta name="generator" content="Docusaurus` to confirm it's the actual site, not a parked page:

```bash
curl -sS https://weaverlet.observatoriogeo.mx/ | grep -o 'generator" content="[^"]*"'
```

### 5. Verify sync (standalone)

This phase is also a **standalone entry point**: when the user asks "is everything synced?" / "did my changes ship?" / "is local in sync with the published site?", jump straight here, skip phases 1 through 4.

Four state stores must agree:

1. Local working tree (no uncommitted edits in `website/`).
2. Local `HEAD`.
3. `origin/main` on GitHub.
4. The SHA of the latest successful workflow run.

```bash
git status --short website/             # expect: empty output
git fetch origin
LOCAL=$(git rev-parse HEAD)
ORIGIN=$(git rev-parse origin/main)
LATEST_RUN=$(gh run list --workflow=docs-deploy.yml --status=success --limit 1 \
              --json headSha --jq '.[0].headSha')

echo "local:    $LOCAL"
echo "origin:   $ORIGIN"
echo "deployed: $LATEST_RUN"
```

**Pass:** all three hashes match AND `git status --short website/` is empty. Report the matched short hash.

**Fail:** read the gap from the mismatch table:

| Symptom | Means | Fix |
|---|---|---|
| `git status --short website/` non-empty | Local website edits never committed | Run phase 2 |
| `local != origin` | Committed, never pushed | `git push origin main` |
| `origin != deployed` AND there is a more-recent run that failed | Build broke; the deployed version is stale | View failure with `gh run view <id> --log-failed`, fix, re-push |
| `origin != deployed` AND no recent run exists | Path filter missed: the push touched only non-`website/**` paths | Trigger `gh workflow run docs-deploy.yml --ref main`, or mirror into `website/` |

## Failure modes worth knowing about

### 1. Trailing-slash drift on directory-index docs (Weaverlet-specific, load-bearing)

**Symptom:** users land at a 404 after clicking through the navbar (e.g., click "Examples" → click "Hello World" → 404 at `/docs/hello-world` instead of `/docs/examples/hello-world`). Build may pass or may fail with broken-link errors depending on where the bad link lives.

**Cause:** a hardcoded `Link to=` or navbar/footer `to:` prop targeting a *directory-index* doc (one backed by an `index.mdx` inside a same-named subdir, e.g. `examples/index.mdx`, `api/index.mdx`) is missing its trailing slash. React Router pushes the no-slash URL on click, then relative MDX links on that page resolve against the no-slash form and drop the directory segment.

**Rule:** for any hardcoded `Link to=...` or navbar/footer `to:` prop under `/docs/`:

- If the target is a **directory-style docs index** (backed by `index.mdx`): **include the trailing slash** → `to: '/docs/examples/'`, `to: '/docs/api/'`.
- If the target is a **single-page doc**: **omit the trailing slash** → `to: '/docs/quickstart'`, `to: '/docs/installation'`, `to: '/docs/changelog'`.
- **Never** set `trailingSlash: true` globally — that flips how Docusaurus' MDX resolver interprets `./` and `../` in source files, breaking dozens of internal links across `signals/`, `routing/`, and `concepts/` (the prior `b9868a6` attempt that was reverted in `065fb12` on the source repo).

Current directory-index docs in this repo: `examples/`, `api/` (in both `docs/` and `versioned_docs/version-0.3.1/`).

Quick audit command:

```bash
grep -rnE 'to[:=][[:space:]]*["\x27]/docs/[^"\x27]*["\x27]' \
  website/src website/docusaurus.config.ts
```

For each match, check whether the target doc has an `index.mdx` in a same-named subdir:

```bash
ls website/versioned_docs/version-*/<path>/index.mdx 2>/dev/null
ls website/docs/<path>/index.mdx 2>/dev/null
```

If it does → trailing slash required. If not → no trailing slash. MDX-resolved links from `[text](./path)` are handled by Docusaurus at build time and do not need manual trailing slashes; only the hardcoded `to:` strings need attention.

### 2. Lock file untracked

**Symptom:** `actions/setup-node@v4` fails with `Some specified paths were not resolved, unable to cache dependencies`. Deploy job is skipped.

**Cause:** `website/package-lock.json` was never committed, or the root `.gitignore`'s broad `package-lock.json` line caught it (the negation `!website/package-lock.json` should prevent this).

**Fix:**

```bash
# Confirm the lock file is tracked
git ls-files website/package-lock.json

# If empty, ensure it is not ignored and re-add
git check-ignore -v website/package-lock.json   # should report only the !-negation hit
git add -f website/package-lock.json
```

### 3. CNAME drift

**Symptom:** `gh api repos/observatoriogeo/weaverlet/pages --jq .cname` returns null or a wrong host. HTTPS cert provisioning fails or the custom domain stops resolving.

**Cause:** `website/static/CNAME` is missing, contains a different host, or has stray whitespace.

**Fix:**

```bash
printf 'weaverlet.observatoriogeo.mx\n' > website/static/CNAME
git add website/static/CNAME && git commit -m "Restore Pages CNAME"
# After deploy:
gh api -X PUT repos/observatoriogeo/weaverlet/pages \
  --field cname=weaverlet.observatoriogeo.mx \
  --field https_enforced=true
```

### 4. HTML comments in hand-written docs

**Symptom:** local `npm run build` fails with an MDX acorn parse error around a `<!--` token in a `.mdx` file under `website/docs/` or `website/versioned_docs/`.

**Cause:** the website's strict-mode MDX 3 parser refuses HTML comments in `.mdx` files.

**Fix:** swap any `<!-- ... -->` to `{/* ... */}` in the offending doc.

### 5. Broken doc id / sidebar reference

**Symptom:** build fails with `Docs version "..." has no doc named "<id>"`, or a navbar item links to a 404 after deploy.

**Cause:** the sidebar (`sidebars.ts` or `versioned_sidebars/version-0.3.1-sidebars.json`) or a navbar/footer item in `docusaurus.config.ts` references an id that no longer matches any file. Or a doc's frontmatter `id:` was changed without updating the references. Versioned sidebars are particularly easy to forget — renaming a file under `versioned_docs/` requires editing the corresponding versioned sidebar JSON.

**Fix:** `grep -l "^id: <missing-id>" website/docs/ website/versioned_docs/` to find the doc; rename the reference or restore the id.

### 6. Path-filter miss

**Symptom:** `gh run list --workflow=docs-deploy.yml --limit 1` shows no new run after a push to `main`.

**Cause:** the push touched only files outside `website/**` and outside `.github/workflows/docs-deploy.yml`. Pure-Python edits to the `weaverlet/` package or test suite do not trigger a docs deploy.

**Fix:**

```bash
gh workflow run docs-deploy.yml --ref main
```

### 7. Pages source drift

**Symptom:** the workflow's `deploy` job fails with a permissions or "Pages not configured" error.

**Cause:** someone toggled repo Settings → Pages → Source from "GitHub Actions" to "Deploy from a branch", or disabled Pages entirely.

**Fix:** check the API.

```bash
gh api repos/observatoriogeo/weaverlet/pages --jq .build_type
# expect: "workflow"
```

If different, set it manually in repo Settings → Pages → "Build and deployment / Source: GitHub Actions" (the Source field is not settable via the public API).

### 8. `https_enforced` got flipped off

**Symptom:** `http://weaverlet.observatoriogeo.mx/` returns 200 instead of a redirect to HTTPS; the Pages API shows `https_enforced: false`.

**Cause:** explicitly toggled off in repo Settings, or auto-reset after a CNAME change via the API.

**Fix:**

```bash
gh api -X PUT repos/observatoriogeo/weaverlet/pages \
  --field https_enforced=true
```

## Debugging unreachable deploys

When live curl returns 4xx / 5xx, walk the chain from outside in.

```bash
# 1. Is the workflow even running?
gh run list --workflow=docs-deploy.yml --limit 3

# 2. Did the latest run succeed?
gh run view <run_id> --json status,conclusion,jobs

# 3. Pages config state
gh api repos/observatoriogeo/weaverlet/pages | python3 -m json.tool

# 4. DNS still resolves correctly?
dig +short weaverlet.observatoriogeo.mx
# Expected:
#   observatoriogeo.github.io.
#   185.199.108.153
#   185.199.109.153
#   185.199.110.153
#   185.199.111.153

# 5. HTTPS cert state
gh api repos/observatoriogeo/weaverlet/pages --jq .https_certificate
# Expect: {"state": "approved", ...}

# 6. Direct curl with -v if the SSL handshake is failing
curl -vsS -o /dev/null https://weaverlet.observatoriogeo.mx/ 2>&1 | head -30
```

Stop and report at the first mismatch; do not redeploy blindly.

## Albatross teardown (one-time, not yet executed)

This site was migrated from Albatross Hub to GitHub Pages. The Albatross deployment is **not** torn down by this skill — see `STAGE2_HANDOFF.md` (initial migration record) for the manual teardown steps. Unlike Dash Sylvereye (where the Albatross variant lives in a *separate* repo), Weaverlet's Albatross bundle was committed into the source `weaverlet-docs` repo under `alba/` — a Jinja2-templated Docker bundle that was deployed to `root@173.255.205.89` via `make deploy`. The teardown therefore involves stopping the container on the Albatross host AND deciding whether to archive `weaverlet-docs` on GitHub or strip its `alba/` subtree.

## Out of scope for this skill

- **Initial GH Pages enablement.** Already done as part of the Stage 2 migration. If somehow disabled, restore via repo Settings → Pages → Source: GitHub Actions.
- **DNS record provisioning.** The CNAME `weaverlet.observatoriogeo.mx -> observatoriogeo.github.io` is configured at the `observatoriogeo.mx` registrar; not changeable from this repo.
- **Cert revocation / renewal.** GitHub auto-manages Let's Encrypt for the custom domain; no manual cert work is needed.
- **Albatross teardown.** Out of scope by design — see the section above. Performed manually once the GitHub Pages deploy is confirmed stable.
- **PyPI release of `weaverlet`.** Separate workflow (manual `python -m build && twine upload`); this skill is docs-only.
