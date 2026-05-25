# Docs migration & GitHub Pages cutover — handoff (Weaverlet)

**Date:** 2026-05-25
**Run mode:** unattended (authorized by the user)
**Outcome:** ✅ green — site live and serving from GitHub Pages

## What shipped

Two-stage migration delivered as **PR #2** (merged to `main`):
<https://github.com/observatoriogeo/weaverlet/pull/2>

### Stage 1 — Docusaurus migration into `website/`

- Source: `observatoriogeo/weaverlet-docs` (separate repo, Docusaurus 3.10, TS config, versioned at 0.3.1, previously hosted on Albatross Hub via the `alba/` subtree inside that same repo).
- Imported into `website/` via `rsync -a --exclude=node_modules --exclude=build --exclude=.docusaurus`. The source's `website/` was already a self-contained Docusaurus project, so no flattening was needed.
- Preserved `versioned_docs/version-0.3.1/`, `versioned_sidebars/version-0.3.1-sidebars.json`, and `versions.json` so the version dropdown survives the move.
- Adapted `docusaurus.config.ts`: `editUrl` retargeted at this repo (`observatoriogeo/weaverlet/edit/main/website/`). `url` / `baseUrl` / `organizationName` / `projectName` were already correct in upstream and needed no change. `onBrokenLinks: 'throw'` and the (absence of) global `trailingSlash` left as-is — both are load-bearing per the source repo's `LINK_CONVENTIONS.md`.
- Added `website/static/CNAME` pinning the custom domain `weaverlet.observatoriogeo.mx`.
- Root `.gitignore` tweaks:
  - Added `!website/package-lock.json` to exempt the lockfile from the broad `package-lock.json` ignore (workflow `setup-node` caches against it).
  - Changed `.claude/` to `.claude/*` and added `!.claude/skills/` so the Stage 2 skill can ship inside the otherwise-ignored `.claude/` tree.
- Skipped from the source repo (Albatross/legacy artifacts not needed on GH Pages): `alba/`, `docs.v1.bak/`, `website.v1.bak/`, `Makefile`, `Dockerfile`, `docker-compose.yml`, `PLAN.md`, the docs repo's own `CLAUDE.md` and `LINK_CONVENTIONS.md`, and the Albatross-specific `.claude/skills/{albatross-deploy,weaverlet-vanity-domain}`.
- Commit: `dedb36d Migrate Docusaurus 3 docs site into website/`.

### Stage 2 — GitHub Pages workflow + reusable skill

- `.github/workflows/docs-deploy.yml` — push-to-main + `workflow_dispatch` triggers; build job (`actions/checkout@v4`, `actions/setup-node@v4` Node 20 with `website/package-lock.json` cache, `npm ci`, `npm run build`, `actions/upload-pages-artifact@v3`); deploy job (`actions/deploy-pages@v4`). Copied verbatim from Whistlerlib's workflow with one substitution (`whistlerlib.observatoriogeo.mx` → `weaverlet.observatoriogeo.mx` in the comment).
- `.claude/skills/docs-deploy/SKILL.md` — project-scoped skill so contributors with Claude Code pick it up automatically. Adapted from Whistlerlib / Dash Sylvereye with three Weaverlet-specific additions:
  1. **Failure Mode #1 — Trailing-slash drift on directory-index docs.** Encodes the rule from the source repo's `LINK_CONVENTIONS.md` (include the slash on `to:` props for `examples/`, `api/`; omit for single-page docs like `quickstart`, `installation`; never set `trailingSlash: true` globally). Includes the audit grep command and the React Router root cause.
  2. **Working with versioned docs** section — explains the `docs/` (next) vs `versioned_docs/version-0.3.1/` (published) split, the `npm run docusaurus docs:version <ver>` command for cutting a new version, and the common "I edited `docs/` but nothing changed live" mistake.
  3. **Albatross teardown** note tailored to Weaverlet's setup (the Albatross bundle lives in `alba/` inside `weaverlet-docs`, not a separate sibling repo as with Dash Sylvereye).
- Commit: `001c116 Add GitHub Pages deploy workflow and docs-deploy skill`.

## Live site

| Probe | URL | Result |
|---|---|---|
| Root (HTTPS) | <https://weaverlet.observatoriogeo.mx/> | 200, `<meta name=generator content="Docusaurus v3.10.1">` |
| Single-page doc (no slash, expected 301) | <https://weaverlet.observatoriogeo.mx/docs/quickstart> | 301 → `/docs/quickstart/` |
| Single-page doc (canonical) | <https://weaverlet.observatoriogeo.mx/docs/quickstart/> | 200 |
| Directory-index doc | <https://weaverlet.observatoriogeo.mx/docs/api/> | 200 |
| Version dropdown | (HTML grep) | `0.3.1` label present — versioned docs intact |

The non-slash `/docs/quickstart` → 301 to `/docs/quickstart/` is GH Pages' standard trailing-slash redirect for HTML served from `<slug>/index.html` (Docusaurus' default output shape). This is expected behavior, matches Dash Sylvereye's deploy, and is documented in the skill.

## Workflow run

First deploy (auto-triggered by the PR #2 merge to `main`):
<https://github.com/observatoriogeo/weaverlet/actions/runs/26387830988>

- build: 1m6s ✓
- deploy: 8s ✓

Workflow emitted the expected Node 20 deprecation annotation (forced migration to Node 24 on 2026-06-02, removal on 2026-09-16). Same exposure as Whistlerlib and Dash Sylvereye — fix in all three repos together when the time comes.

## GitHub Pages state (post-cutover)

```
build_type:    workflow
cname:         weaverlet.observatoriogeo.mx
https_enforced: true
https_certificate.state: approved (expires 2026-08-23)
source:        branch=main, path=/
```

Cert provisioning took ~30 seconds from the `gh api -X PUT … cname=…` call to `state=approved` (DNS was already configured for the parent observatoriogeo.mx zone, so no DNS-01 challenge propagation delay).

## Manual step still pending — Albatross teardown

The Albatross deployment is **intentionally still running** at the same hostname via the existing nginx edge — until DNS flips at the registrar, the two deploys coexist and the live URL was already pointing at GH Pages by the time this PR merged. To formally tear down the Albatross side once you're happy with the GH Pages deploy:

1. **Stop the Docker container on Albatross Hub.** Host is `root@173.255.205.89` (see `[[Albatross Hub]]` in the IIxM vault for the docker stack name and SSH details). The container builds from `weaverlet-docs/alba/` and serves the docs behind the nginx reverse proxy.
2. **Decide on `weaverlet-docs/alba/`.** Two options:
   - Keep the subtree committed for posterity (it's the historical record of how the Albatross variant was wired). Adds zero ongoing cost.
   - Strip the subtree from `weaverlet-docs` and commit the removal. Cleaner repo, but harder to revert if you ever need to put the Albatross deploy back up.
3. **Decide on the `weaverlet-docs` repo itself.** Now that this repo owns the canonical docs source, `observatoriogeo/weaverlet-docs` is functionally superseded. Two options:
   - Archive it on GitHub (preserves history, prevents accidental edits, sends a clear "use the new repo" signal).
   - Point its README at this repo's `website/` subtree and leave it active (useful if you want incoming search-engine traffic to redirect users gracefully).
4. **DNS check.** The CNAME `weaverlet.observatoriogeo.mx -> observatoriogeo.github.io` should already be in place (the GH Pages cert provisioning would have failed otherwise). Confirm with `dig +short weaverlet.observatoriogeo.mx` — expected: `observatoriogeo.github.io.` plus the four `185.199.10X.153` GitHub Pages IPs.

The DNS record was apparently the one piece of infrastructure that was already pointing at GitHub Pages before the migration ran — the user mentioned the CNAME was ready, and the immediate `approved` state of the cert confirmed this. Worth double-checking before the Albatross teardown that nothing else is still pointing at the Albatross IP.

## Weaverlet-specific gotchas hit during the run

1. **`.claude/` ignore had to use a `.claude/*` glob, not `.claude/`.** First attempt used `.claude/` + `!.claude/skills/` and the negation didn't take — `git check-ignore` still matched the directory. Fixed by changing the parent pattern to `.claude/*` (which only ignores immediate children, allowing the `!.claude/skills/` re-include to work). Captured in the Stage 2 commit message and the `.gitignore` itself.
2. **Trailing-slash audit was clean** — the source `docusaurus.config.ts` was already correct (slashes on `examples/`, `api/`; no slash on `installation`, `quickstart`, `changelog`). No fix needed, but the skill documents the rule loudly because it would be the most likely re-introduction point.
3. **One transient SSL SAN mismatch** during the very first round of smoke probes (the second of three curls returned `SSL: no alternative certificate subject name matches target host name`). Self-resolved within 10 seconds on retry — looks like cert deploy propagation through GitHub's edge. Not blocking; mentioning in case it surfaces again on a later deploy.
4. **The pre-existing untracked `.plans/` and `lancedb/` directories were left alone.** Both pre-date this run; neither has anything to do with the docs migration.

## Things to know going forward

- The skill at `.claude/skills/docs-deploy/SKILL.md` is the single source of truth for "how to ship a docs change." It documents the four-phase deploy loop, a sync-check standalone entry point, and eight failure modes (trailing-slash being #1 since it's Weaverlet-specific).
- `website/package-lock.json` **must stay tracked** — the workflow's `setup-node` step caches against it. The root `.gitignore` exempts it explicitly. If anyone ever drops the `!website/package-lock.json` line, the next deploy will fail with `Some specified paths were not resolved` — see Failure Mode #2 in the skill.
- The `docs-deploy.yml` workflow uses Node 20 actions (`actions/checkout@v4`, `setup-node@v4`, `upload-artifact@v4`). GitHub deprecated Node 20 on 2025-09-19; they'll force-migrate to Node 24 on 2026-06-02 and remove Node 20 entirely on 2026-09-16. Whistlerlib and Dash Sylvereye have the same exposure — fix in all three together when the time comes.
- The branch `docs/migrate-to-github-pages` was deleted on merge (`gh pr merge --merge --delete-branch`). Nothing to clean up.

## Pre-existing dirty state not touched by this run

The working tree had two pre-existing untracked entries that I deliberately left alone:

- `.plans/` — the migration prompt itself plus any other planning docs.
- `lancedb/` — empty scratch directory.

Neither is mine. Review and commit (or git-ignore) them yourself if appropriate. Both are already covered by the existing `.gitignore` for `lancedb/` and the lack of any pattern matching `.plans/` (so it shows as untracked but won't be picked up accidentally).
